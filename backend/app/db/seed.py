"""Idempotently seed synthetic local demo data."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.core.settings import Settings
from app.db.session import SessionLocal
from app.models import Account, Admin, TollPrice, TrafficRecord, User, Vehicle, WalletLedgerEntry
from app.services.auth.service import hash_password


def seed_demo_data() -> None:
    settings = Settings()
    with SessionLocal.begin() as database:
        admin = database.scalar(select(Admin).where(Admin.email == settings.demo_admin_email))
        if admin is None:
            database.add(
                Admin(
                    email=settings.demo_admin_email,
                    display_name="Demo Administrator",
                    password_hash=hash_password(settings.demo_admin_password),
                )
            )
        elif admin.password_hash is None:
            admin.password_hash = hash_password(settings.demo_admin_password)

        demo_people = (
            (
                "Aina Rahman",
                "aina.rahman@example.test",
                "+60123456789",
                "VAA1234",
                "Proton",
                "X50",
                "White",
                Decimal("50.00"),
            ),
            (
                "Daniel Lee",
                "daniel.lee@example.test",
                "+60187654321",
                "WXY5678",
                "Perodua",
                "Myvi",
                "Blue",
                Decimal("12.00"),
            ),
            (
                "Siti Hajar",
                "siti.hajar@example.test",
                "+60111222333",
                "JTU9090",
                "Honda",
                "City",
                "Silver",
                Decimal("1.50"),
            ),
            (
                "Kumaravel Raj",
                "kumaravel.raj@example.test",
                "+60135556677",
                "BKV2026",
                "Toyota",
                "Hilux",
                "Black",
                Decimal("85.75"),
            ),
            (
                "Mei Ling Tan",
                "mei.ling.tan@example.test",
                "+60178889900",
                "VDR8812",
                "Tesla",
                "Model 3",
                "Red",
                Decimal("6.20"),
            ),
            (
                "Farid Iskandar",
                "farid.iskandar@example.test",
                "+60194443322",
                "BQR7310",
                "Yamaha",
                "NVX",
                "Grey",
                Decimal("0.80"),
            ),
        )
        for name, email, phone, plate, make, model, color, balance in demo_people:
            user = database.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(full_name=name, email=email, phone=phone)
                database.add(user)
                database.flush()
            account = database.scalar(select(Account).where(Account.user_id == user.id))
            if account is None:
                account = Account(user_id=user.id, balance=balance, opening_balance=balance, is_primary=True)
                database.add(account)
                database.flush()
            if database.scalar(select(WalletLedgerEntry).where(WalletLedgerEntry.account_id == account.id)) is None:
                database.add(WalletLedgerEntry(
                    account_id=account.id, entry_type="opening_balance", amount=account.opening_balance,
                    direction="credit", balance_after=account.balance,
                    description="Opening simulated wallet balance.", idempotency_key=f"seed-opening:{account.id}",
                ))
            if database.scalar(select(Vehicle).where(Vehicle.plate_number == plate)) is None:
                database.add(
                    Vehicle(
                        user_id=user.id, plate_number=plate, make=make, model=model, color=color
                    )
                )

        if database.scalar(select(TrafficRecord).limit(1)) is None:
            now = datetime.now(UTC)
            traffic = TrafficRecord(
                measured_at=now,
                vehicle_count=24,
                road_capacity=100,
                congestion_percentage=Decimal("24.00"),
                congestion_category="low",
                scenario="normal",
            )
            database.add(traffic)
            database.flush()
            database.add(
                TollPrice(
                    traffic_record_id=traffic.id,
                    effective_at=now,
                    amount=Decimal("2.00"),
                    congestion_category="low",
                    rule_version="v1",
                )
            )


if __name__ == "__main__":
    seed_demo_data()
    print("Synthetic demo data is ready.")
