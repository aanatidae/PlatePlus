from decimal import Decimal
from random import Random
from types import SimpleNamespace

from app.db.seed import DEMO_VEHICLE_TARGET, synthetic_demo_people
from app.services.demo_feed import crossing_interval_seconds, select_demo_vehicle
from alpr.plate.normalization import is_plausible_malaysian_plate


def test_congestion_controls_demo_crossing_cadence():
    assert crossing_interval_seconds(Decimal("10")) > crossing_interval_seconds(Decimal("35"))
    assert crossing_interval_seconds(Decimal("35")) > crossing_interval_seconds(Decimal("55"))
    assert crossing_interval_seconds(Decimal("55")) > crossing_interval_seconds(Decimal("75"))
    assert crossing_interval_seconds(Decimal("75")) > crossing_interval_seconds(Decimal("95"))


def test_demo_cadence_is_bounded_even_with_jitter():
    assert crossing_interval_seconds(Decimal("100"), jitter=-99) == 0.8
    assert crossing_interval_seconds(Decimal("0"), jitter=0) == 10.0


def test_seeded_presentation_fleet_is_large_unique_and_plate_plausible():
    fleet = synthetic_demo_people()

    assert len(fleet) == DEMO_VEHICLE_TARGET == 96
    plates = [person[3] for person in fleet]
    assert len(plates) == len(set(plates))
    assert all(is_plausible_malaysian_plate(plate) for plate in plates)
    assert any(person[-1] < Decimal("2.00") for person in fleet)


def test_demo_selection_suppresses_recent_location_and_global_plates():
    vehicles = [SimpleNamespace(plate_number=f"VAA{1000 + index}") for index in range(30)]
    recent = {vehicle.plate_number for vehicle in vehicles[:16]}

    choice = select_demo_vehicle(vehicles, recent, Random(7))

    assert choice.plate_number not in recent
