from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import (
    AdminAuditLog,
    DynamicPricingRule,
    TollLocation,
    TollPrice,
    TrafficRecord,
    TrafficSimulationSettings,
)
from app.services.traffic.simulation import (
    MALAYSIA_TIMEZONE,
    average_speed_for_profile,
    profile_congestion_for_time,
    rule_for_congestion,
    run_network_simulation,
    run_simulation,
)


def test_traffic_routes_require_administrator_authentication(database_app) -> None:
    response = TestClient(database_app).get("/api/traffic/settings")

    assert response.status_code == 401
    assert response.json() == {"detail": "Administrator authentication is required."}


def test_admin_can_run_a_fixed_scenario_and_persist_its_matching_price(
    database, database_app, admin_auth_headers
) -> None:
    client = TestClient(database_app)
    settings_response = client.put(
        "/api/traffic/settings",
        json={
            "is_enabled": False,
            "interval_minutes": 5,
            "simulation_mode": "fixed_scenario",
            "fixed_scenario": "severe",
            "time_mode": "simulated",
            "simulated_time": "2026-09-02T08:00:00Z",
        },
        headers=admin_auth_headers,
    )
    assert settings_response.status_code == 200, settings_response.text

    response = client.post(
        "/api/traffic/simulate", json={"scenario": "severe"}, headers=admin_auth_headers
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["scenario"] == "severe"
    assert body["congestion_category"] == "severe"
    assert body["amount"] == "5.00"
    assert Decimal(body["congestion_percentage"]) >= Decimal("80.01")
    assert database.scalar(select(TrafficRecord)) is not None
    assert database.scalar(select(TollPrice)) is not None
    assert database.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "traffic_simulation_run"))


def test_pricing_rule_change_creates_a_new_current_price_and_audit_entry(
    database, database_app, admin_auth_headers
) -> None:
    client = TestClient(database_app)
    settings = database.scalar(select(TrafficSimulationSettings))
    assert settings is not None
    run_simulation(
        database,
        settings,
        source="manual",
        scenario="normal",
        now=datetime(2026, 9, 2, tzinfo=UTC),
        seed=7,
    )
    database.commit()
    response = client.put(
        "/api/traffic/pricing-rules",
        json={
            "rules": [
                {"scenario": "normal", "minimum_percentage": "0", "maximum_percentage": "30", "multiplier": "1.25"},
                {"scenario": "moderate", "minimum_percentage": "30.01", "maximum_percentage": "60", "multiplier": "1.75"},
                {"scenario": "peak_hour", "minimum_percentage": "60.01", "maximum_percentage": "80", "multiplier": "2.25"},
                {"scenario": "severe", "minimum_percentage": "80.01", "maximum_percentage": "100", "multiplier": "2.75"},
            ]
        },
        headers=admin_auth_headers,
    )

    assert response.status_code == 200, response.text
    latest_price = database.scalar(select(TollPrice).order_by(TollPrice.effective_at.desc()))
    assert latest_price is not None
    assert latest_price.amount == Decimal("2.50")
    assert latest_price.rule_version == "v2"
    assert database.scalar(select(AdminAuditLog).where(AdminAuditLog.action == "pricing_rules_updated"))


def test_network_simulation_persists_independent_profiles_and_excludes_webcam_toll(database) -> None:
    settings = database.scalar(select(TrafficSimulationSettings))
    assert settings is not None
    results = run_network_simulation(
        database, settings, source="scheduled", now=datetime(2026, 9, 1, 23, tzinfo=UTC), seed=4
    )
    database.commit()

    assert {result.traffic_record.location.code for result in results} == {"PENCHALA", "DUKE", "KESAS", "NPE"}
    states = {result.traffic_record.location.code: result.traffic_record for result in results}
    assert states["DUKE"].congestion_percentage != states["NPE"].congestion_percentage
    assert states["DUKE"].congestion_category in {"low", "moderate", "high", "severe"}
    assert states["NPE"].congestion_category in {"low", "moderate", "high", "severe"}
    assert states["DUKE"].vehicle_count != states["NPE"].vehicle_count
    assert {result.toll_price.location_id for result in results} == {
        result.traffic_record.location_id for result in results
    }
    assert {
        result.toll_price.congestion_category for result in results
    } == {
        result.traffic_record.congestion_category for result in results
    }
    assert database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR")) is not None


def test_tuned_location_profiles_follow_distinct_daily_patterns_and_preserve_webcam_toll(database) -> None:
    rules = {
        rule.scenario: rule
        for rule in database.scalars(select(DynamicPricingRule))
    }
    locations = {
        location.code: location
        for location in database.scalars(select(TollLocation).where(TollLocation.code != "SIMULATOR"))
    }
    representative_hours = (2, 7, 8, 10, 13, 17, 18, 21, 23)
    matrix = {
        code: {
            hour: profile_congestion_for_time(
                location, datetime(2026, 9, 2, hour, tzinfo=MALAYSIA_TIMEZONE)
            )
            for hour in representative_hours
        }
        for code, location in locations.items()
    }

    print("\nTuned location traffic matrix (MYT):")
    for hour in representative_hours:
        print(
            f"{hour:02}:00 "
            + " | ".join(
                f"{code} {matrix[code][hour]}%/{rule_for_congestion(rules, matrix[code][hour]).scenario}"
                for code in ("PENCHALA", "DUKE", "NPE", "KESAS")
            )
        )

    categories = {
        code: {hour: rule_for_congestion(rules, percentage).scenario for hour, percentage in samples.items()}
        for code, samples in matrix.items()
    }
    assert categories["PENCHALA"][2] == "normal"
    assert categories["PENCHALA"][7] in {"moderate", "peak_hour"}
    assert categories["PENCHALA"][18] in {"moderate", "peak_hour"}
    assert categories["PENCHALA"][21] == "normal"
    assert categories["DUKE"][2] == "normal"
    assert categories["DUKE"][10] == "moderate"
    assert categories["DUKE"][7] in {"peak_hour", "severe"}
    assert categories["DUKE"][18] in {"peak_hour", "severe"}
    assert categories["DUKE"][21] == "normal"
    assert {categories["NPE"][hour] for hour in representative_hours} >= {"normal", "moderate", "peak_hour"}
    assert categories["NPE"][21] == "normal"
    assert {categories["KESAS"][hour] for hour in representative_hours} >= {"normal", "moderate", "peak_hour"}
    assert categories["KESAS"][21] == "normal"
    assert len({matrix[code][13] for code in matrix}) == len(matrix)
    assert matrix["DUKE"][2] == profile_congestion_for_time(
        locations["DUKE"], datetime(2026, 9, 2, 2, 0, 45, tzinfo=MALAYSIA_TIMEZONE)
    )
    for code, location in locations.items():
        assert average_speed_for_profile(location, matrix[code][2]) > average_speed_for_profile(
            location, matrix[code][18]
        )
    simulator = database.scalar(select(TollLocation).where(TollLocation.code == "SIMULATOR"))
    assert simulator is not None
    assert simulator.road_capacity == 10
    assert simulator.simulation_profile["telemetry_source"] == "webcam_alpr"
