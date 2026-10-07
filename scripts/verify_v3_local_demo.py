"""Operator-run localhost smoke check with fictional optical fixtures.

Run from backend using the installed environment. This intentionally creates
simulated demo payments/history, never resets data, and never accesses a camera.
Requires an already-running local API, PostgreSQL, weights and cached OCR assets.
"""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import requests
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import func, select, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.settings import Settings
from app.db.seed import seed_demo_data
from app.db.session import SessionLocal
from app.models import (
    Account,
    DetectionRecord,
    TollLocation,
    TollPrice,
    TollTransaction,
    TrafficRecord,
    TrafficSimulationSettings,
    User,
    Vehicle,
    WalletLedgerEntry,
)
from app.services.traffic.pricing import decide_price

BASE = "http://127.0.0.1:8000"
OUTPUT = ROOT / ".plateplus-demo" / "qa-y"


def snapshot(database):
    models = [
        User,
        Account,
        Vehicle,
        DetectionRecord,
        TollTransaction,
        TrafficRecord,
        TollPrice,
        WalletLedgerEntry,
    ]
    return {
        "counts": {
            model.__tablename__: database.scalar(
                select(func.count()).select_from(model)
            )
            for model in models
        },
        "wallets": {
            str(item.id): str(item.balance)
            for item in database.scalars(select(Account).order_by(Account.id))
        },
    }


def fixture(plate):
    """Draw a fictional plate/vehicle test scene; no real vehicle photo is used."""
    image = Image.new("RGB", (1000, 600), (100, 100, 105))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (90, 90, 910, 520), 45, fill=(180, 185, 190), outline=(35, 35, 35), width=8
    )
    draw.rectangle((140, 150, 860, 250), fill=(35, 40, 45))
    draw.rectangle((250, 290, 750, 430), fill="black", outline="white", width=3)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 80)
    draw.text((500, 360), plate, font=font, fill="white", anchor="mm")
    path = OUTPUT / f"{plate}.png"
    image.save(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--create-demo-events",
        action="store_true",
        required=True,
        help="Create audited simulated payments/history using fictional plate fixtures.",
    )
    parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    assert settings.yolo_model_path.is_file(), (
        "Provide the existing local YOLO weights."
    )
    for model in ["PP-OCRv6_medium_det", "PP-OCRv6_medium_rec"]:
        assert (
            settings.paddleocr_model_storage
            / "official_models"
            / model
            / "inference.pdiparams"
        ).is_file(), "Provide cached OCR assets; this check must not download models."
    # This is a development demo, never a destructive integration fixture.
    from sqlalchemy.engine import make_url

    assert make_url(settings.sqlalchemy_database_url).host in {"localhost", "127.0.0.1"}
    session = requests.Session()
    health = session.get(BASE + "/health", timeout=15)
    health.raise_for_status()
    login = session.post(
        BASE + "/api/auth/login",
        json={
            "email": settings.demo_admin_email,
            "password": settings.demo_admin_password,
        },
        timeout=15,
    )
    login.raise_for_status()
    session.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    feed = session.get(BASE + "/api/operations/demo/feed", timeout=15)
    feed.raise_for_status()
    assert not feed.json()["running"], (
        "Pause Live Feed before checking seed/replay isolation."
    )
    report = {
        "checked_at": datetime.now(UTC).isoformat(),
        "physical_camera": "deferred by user",
        "health": health.json(),
    }
    locations = session.get(BASE + "/api/locations", timeout=15).json()
    assert {item["code"] for item in locations} == {
        "LDP",
        "AKLEH",
        "NPE",
        "GRAND_SAGA",
        "SIMULATOR",
    }
    simulator = next(item["id"] for item in locations if item["code"] == "SIMULATOR")
    report["locations"] = locations
    with SessionLocal() as database:
        head = database.execute(
            text("select version_num from alembic_version")
        ).scalar_one()
        assert head == "20261007_0014"
        report["migration_head"] = head
        before = snapshot(database)
    seed_demo_data()
    with SessionLocal() as database:
        assert snapshot(database) == before, (
            "Repeat seed changed existing wallets or records"
        )
    report["repeat_seed_preserved_counts_and_wallets"] = True
    # Read-only pricing decisions exercise the actual saved rules and safeguards.
    with SessionLocal() as database:
        policy = database.scalar(select(TrafficSimulationSettings))
        report["pricing"] = []
        for location in database.scalars(
            select(TollLocation).where(
                TollLocation.status == "operational", TollLocation.code != "SIMULATOR"
            )
        ):
            decisions = [
                decide_price(
                    database, policy, location, Decimal(value), context="policy_update"
                )
                for value in ["15", "45", "70", "90"]
            ]
            assert decisions[0].amount < decisions[-1].amount
            report["pricing"].append(
                {
                    "location": location.code,
                    "band_prices": [str(item.amount) for item in decisions],
                }
            )
    run_key = "v3-y-" + str(uuid4())
    report["optical_results"] = []

    def upload(plate, key, route="/api/webcam/images", field="image"):
        path = fixture(plate)
        with path.open("rb") as file:
            response = session.post(
                BASE + route,
                params={"location_id": simulator} if field == "image" else {},
                headers={"Idempotency-Key": key},
                files={field: (path.name, file, "image/png")},
                timeout=240,
            )
        response.raise_for_status()
        result = response.json()
        assert result["plate_text"] == plate, result
        print(plate, result["plate_origin"], result["payment_status"], flush=True)
        return result

    for plate, origin, expected in [
        ("VAA1234", "malaysian", "successful"),
        ("GBC6427R", "singaporean", "successful"),
        ("YN4821R", "singaporean", "insufficient_balance"),
        ("SBA1234A", "unknown", "low_confidence"),
    ]:
        key = run_key + "-" + plate
        result = upload(plate, key)
        assert (
            result["plate_origin"] == origin and result["payment_status"] == expected
        ), result
        assert Decimal(str(result["payment_amount"])) == Decimal(
            str(result["payment_dynamic_toll_amount"])
        ) + Decimal(str(result["payment_foreign_vehicle_charge"]))
        if origin == "malaysian":
            assert result["payment_foreign_vehicle_charge"] == 0
        if origin == "unknown":
            assert not result["charge_eligible"] and result["payment_amount"] == 0
        with SessionLocal() as database:
            transaction = database.scalar(
                select(TollTransaction).where(TollTransaction.idempotency_key == key)
            )
            assert (
                transaction.is_simulated and str(transaction.location_id) == simulator
            )
            entries = list(
                database.scalars(
                    select(WalletLedgerEntry).where(
                        WalletLedgerEntry.transaction_id == transaction.id
                    )
                )
            )
            assert len(entries) == (1 if expected == "successful" else 0)
            if entries:
                assert entries[0].amount == transaction.amount
            replay_before = snapshot(database)
        replay = upload(plate, key)
        assert replay["payment_duplicate"] is True
        with SessionLocal() as database:
            assert snapshot(database) == replay_before
        report["optical_results"].append(
            {"plate": plate, "result": result, "idempotent_replay": True}
        )
    started = session.post(BASE + "/api/webcam/sessions", timeout=15)
    started.raise_for_status()
    session_id = started.json()["session_id"]
    try:
        frame = upload(
            "XD7316E",
            run_key + "-frame",
            f"/api/webcam/sessions/{session_id}/frames",
            "frame",
        )
        assert (
            frame["payment_status"] == "successful"
            and frame["plate_origin"] == "singaporean"
        )
        duplicate = upload("XD7316E", run_key + "-duplicate", field="image")
        assert (
            duplicate["status"] == "duplicate_plate_within_cooldown"
            and duplicate["payment_status"] is None
        )
        report["webcam_api_with_fictional_still_frame"] = frame
        report["cross_input_cooldown"] = duplicate
    finally:
        stopped = session.delete(
            BASE + f"/api/webcam/sessions/{session_id}", timeout=15
        )
        assert stopped.status_code == 204
    live_path = BASE + f"/api/locations/{simulator}/live"
    active = session.get(live_path, timeout=15).json()
    assert active["telemetry"]["active_crossings"] >= 4
    assert active["telemetry"]["average_speed_kmh"] is None
    report["simulator_active"] = active
    print(
        "Active Simulator crossings verified; observing real 60-second expiry...",
        flush=True,
    )
    for _ in range(7):
        time.sleep(9)
    expired = session.get(live_path, timeout=15).json()
    assert expired["telemetry"]["active_crossings"] == 0
    assert float(expired["telemetry"]["congestion_percentage"]) == 0
    assert (
        expired["telemetry"]["last_crossing_at"]
        == active["telemetry"]["last_crossing_at"]
    )
    report["simulator_expired"] = expired
    with SessionLocal() as database:
        report["prediction_baseline"] = snapshot(database)
    (OUTPUT / "api-results.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf8"
    )
    print(
        "Local optical/payment/window checks passed; evidence saved in .plateplus-demo/qa-y/api-results.json",
        flush=True,
    )


if __name__ == "__main__":
    main()
