"""
SAR Guardian — Demo Data Seed Script

Creates:
- 3 demo users (admin, supervisor, analyst)
- 2 sample cases with transactions, rule triggers
- Immutable log entries for audit trail

Usage:
    python seed.py
    
Or via Docker:
    docker-compose exec backend python seed.py
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.database import Base
from app.models.user import User, UserRole
from app.models.case import Case, CaseStatus
from app.models.transaction import Transaction
from app.models.rule_trigger import RuleTrigger
from app.services.auth_service import hash_password
from app.services.audit_service import write_immutable_log


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as db:
        # ===== USERS =====
        admin = User(
            id=uuid.uuid4(),
            name="System Admin",
            email="admin@sarguardian.com",
            role=UserRole.admin,
            hashed_password=hash_password("Admin@123"),
        )
        supervisor = User(
            id=uuid.uuid4(),
            name="Sarah Chen",
            email="supervisor@sarguardian.com",
            role=UserRole.supervisor,
            hashed_password=hash_password("Super@123"),
        )
        analyst = User(
            id=uuid.uuid4(),
            name="Michael Torres",
            email="analyst@sarguardian.com",
            role=UserRole.analyst,
            hashed_password=hash_password("Analyst@123"),
        )
        db.add_all([admin, supervisor, analyst])
        await db.flush()

        # ===== CASE 1 — Structuring / Smurfing =====
        case1 = Case(
            id=uuid.uuid4(),
            customer_id="CUST-2026-001",
            customer_name="Robert Kline",
            customer_type="individual",
            customer_risk_rating="HIGH",
            kyc_id_type="passport",
            kyc_id_number="US8837291",
            kyc_country="United States",
            kyc_occupation="Import/Export Business Owner",
            kyc_onboarding_date=datetime(2023, 3, 15, tzinfo=timezone.utc),
            account_number="ACC-10042891",
            account_type="business_checking",
            account_open_date=datetime(2023, 3, 20, tzinfo=timezone.utc),
            account_balance=87432.50,
            account_currency="USD",
            alert_id="ALERT-2026-STR-001",
            alert_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
            alert_type="structuring",
            alert_score=88.5,
            status=CaseStatus.open,
            notes="Customer flagged for multiple cash deposits just below $10,000 CTR threshold over a 10-day period.",
            historical_avg_monthly_volume=45000.0,
            historical_avg_transaction_size=8500.0,
            historical_counterparty_count=8,
            historical_sar_count=0,
            composite_risk_score=82.0,
            network_risk_score=65.0,
            behavioral_risk_score=78.0,
            graph_analysis="Subject connected to 3 entities with shared beneficial ownership. Two entities registered in Delaware with minimal public filings. Fund flows show circular pattern: Subject → Entity A → Entity B → Subject within 5-day windows.",
        )
        db.add(case1)
        await db.flush()

        # Transactions for Case 1
        base_date = datetime(2026, 2, 1, tzinfo=timezone.utc)
        case1_transactions = [
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-001", amount=9800.00, currency="USD",
                       transaction_date=base_date, transaction_type="cash_deposit", direction="inbound",
                       counterparty_name="Cash Deposit", country="United States", purpose="business revenue", is_flagged=True),
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-002", amount=9500.00, currency="USD",
                       transaction_date=base_date + timedelta(days=1), transaction_type="cash_deposit", direction="inbound",
                       counterparty_name="Cash Deposit", country="United States", purpose="business revenue", is_flagged=True),
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-003", amount=9700.00, currency="USD",
                       transaction_date=base_date + timedelta(days=2), transaction_type="cash_deposit", direction="inbound",
                       counterparty_name="Cash Deposit", country="United States", purpose="business revenue", is_flagged=True),
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-004", amount=9900.00, currency="USD",
                       transaction_date=base_date + timedelta(days=4), transaction_type="cash_deposit", direction="inbound",
                       counterparty_name="Cash Deposit", country="United States", purpose="business revenue", is_flagged=True),
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-005", amount=9600.00, currency="USD",
                       transaction_date=base_date + timedelta(days=5), transaction_type="cash_deposit", direction="inbound",
                       counterparty_name="Cash Deposit", country="United States", purpose="business revenue", is_flagged=True),
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-006", amount=28000.00, currency="USD",
                       transaction_date=base_date + timedelta(days=6), transaction_type="wire", direction="outbound",
                       counterparty_name="Apex Trading LLC", counterparty_bank="First Delaware Bank",
                       country="United States", purpose="inventory purchase"),
            Transaction(case_id=case1.id, transaction_ref="TXN-STR-007", amount=19500.00, currency="USD",
                       transaction_date=base_date + timedelta(days=8), transaction_type="wire", direction="outbound",
                       counterparty_name="Pacific Rim Imports", counterparty_bank="HSBC Hong Kong",
                       country="Hong Kong", purpose="supplier payment", is_flagged=True),
        ]
        db.add_all(case1_transactions)

        # Rule Triggers for Case 1
        case1_triggers = [
            RuleTrigger(case_id=case1.id, rule_code="AML-STR-001", rule_description="Cash deposits below CTR threshold in rolling 10-day window",
                       threshold_value=10000.0, actual_value=9800.0, breached=True,
                       typology_code="STRUCTURING", typology_description="Structuring/Smurfing — deposits structured below $10,000 CTR threshold"),
            RuleTrigger(case_id=case1.id, rule_code="AML-VEL-001", rule_description="Velocity spike — number of cash deposits exceeds 3x historical monthly average",
                       threshold_value=3.0, actual_value=5.0, breached=True,
                       typology_code="VELOCITY_SPIKE", typology_description="Unusual increase in transaction frequency"),
            RuleTrigger(case_id=case1.id, rule_code="AML-XBR-001", rule_description="Cross-border wire to high-risk jurisdiction",
                       threshold_value=15000.0, actual_value=19500.0, breached=True,
                       typology_code="CROSS_BORDER", typology_description="Cross-border funds movement to high-risk jurisdiction"),
        ]
        db.add_all(case1_triggers)

        # ===== CASE 2 — Layering =====
        case2 = Case(
            id=uuid.uuid4(),
            customer_id="CUST-2026-002",
            customer_name="Meridian Holdings Ltd",
            customer_type="entity",
            customer_risk_rating="MEDIUM",
            kyc_id_type="incorporation_cert",
            kyc_id_number="UK-CO-9912847",
            kyc_country="United Kingdom",
            kyc_occupation="Investment Holding Company",
            kyc_onboarding_date=datetime(2024, 6, 1, tzinfo=timezone.utc),
            account_number="ACC-20071553",
            account_type="corporate",
            account_open_date=datetime(2024, 6, 10, tzinfo=timezone.utc),
            account_balance=1245000.00,
            account_currency="USD",
            alert_id="ALERT-2026-LAY-002",
            alert_date=datetime(2026, 2, 15, tzinfo=timezone.utc),
            alert_type="layering",
            alert_score=72.0,
            status=CaseStatus.open,
            notes="Entity receiving funds from multiple jurisdictions and rapidly disbursing to shell entities.",
            historical_avg_monthly_volume=200000.0,
            historical_avg_transaction_size=50000.0,
            historical_counterparty_count=12,
            historical_sar_count=1,
            composite_risk_score=68.0,
            network_risk_score=75.0,
            behavioral_risk_score=62.0,
            graph_analysis="Meridian Holdings connected to 7 entities across 4 jurisdictions. Layered fund flows: Entity C (BVI) → Meridian → Entity D (Panama) → Entity E (Singapore). Beneficial ownership opaque for 3 downstream entities.",
        )
        db.add(case2)
        await db.flush()

        # Transactions for Case 2
        case2_base = datetime(2026, 1, 15, tzinfo=timezone.utc)
        case2_transactions = [
            Transaction(case_id=case2.id, transaction_ref="TXN-LAY-001", amount=350000.00, currency="USD",
                       transaction_date=case2_base, transaction_type="wire", direction="inbound",
                       counterparty_name="Global Ventures BVI", counterparty_bank="Cayman National",
                       country="British Virgin Islands", purpose="investment return"),
            Transaction(case_id=case2.id, transaction_ref="TXN-LAY-002", amount=275000.00, currency="USD",
                       transaction_date=case2_base + timedelta(days=2), transaction_type="wire", direction="inbound",
                       counterparty_name="Pacific Trust Co", counterparty_bank="DBS Singapore",
                       country="Singapore", purpose="consulting fees"),
            Transaction(case_id=case2.id, transaction_ref="TXN-LAY-003", amount=180000.00, currency="USD",
                       transaction_date=case2_base + timedelta(days=3), transaction_type="wire", direction="outbound",
                       counterparty_name="Estrella Assets Panama", counterparty_bank="Banco General",
                       country="Panama", purpose="management fees", is_flagged=True),
            Transaction(case_id=case2.id, transaction_ref="TXN-LAY-004", amount=220000.00, currency="USD",
                       transaction_date=case2_base + timedelta(days=5), transaction_type="wire", direction="outbound",
                       counterparty_name="Nexus Capital SG", counterparty_bank="OCBC Singapore",
                       country="Singapore", purpose="investment placement", is_flagged=True),
            Transaction(case_id=case2.id, transaction_ref="TXN-LAY-005", amount=150000.00, currency="EUR",
                       transaction_date=case2_base + timedelta(days=7), transaction_type="wire", direction="outbound",
                       counterparty_name="Atlas Holding GmbH", counterparty_bank="Deutsche Bank",
                       country="Germany", purpose="acquisition deposit"),
        ]
        db.add_all(case2_transactions)

        # Rule Triggers for Case 2
        case2_triggers = [
            RuleTrigger(case_id=case2.id, rule_code="AML-LAY-001", rule_description="Rapid fund pass-through — funds received and disbursed within 7 days",
                       threshold_value=7.0, actual_value=5.0, breached=True,
                       typology_code="LAYERING", typology_description="Complex layering — rapid movement of funds through multiple jurisdictions"),
            RuleTrigger(case_id=case2.id, rule_code="AML-JUR-001", rule_description="Transactions involving 3+ high-risk jurisdictions",
                       threshold_value=3.0, actual_value=4.0, breached=True,
                       typology_code="HIGH_RISK_JURISDICTION", typology_description="Funds movement through jurisdictions with weak AML controls"),
            RuleTrigger(case_id=case2.id, rule_code="AML-VOL-001", rule_description="Monthly volume exceeds 3x historical average",
                       threshold_value=600000.0, actual_value=1175000.0, breached=True,
                       typology_code="VOLUME_SPIKE", typology_description="Significant deviation from historical transaction volume"),
        ]
        db.add_all(case2_triggers)

        # Log entries
        await write_immutable_log(db, "system", "seed", "data_seeded", str(admin.id), "Demo data seeded successfully")

        await db.commit()

    await engine.dispose()
    print("\n✅ Seed data created successfully!")
    print("═" * 50)
    print("Demo Users:")
    print(f"  Admin:      admin@sarguardian.com / Admin@123")
    print(f"  Supervisor: supervisor@sarguardian.com / Super@123")
    print(f"  Analyst:    analyst@sarguardian.com / Analyst@123")
    print(f"\nDemo Cases:")
    print(f"  Case 1: Robert Kline — Structuring (7 transactions, 3 triggers)")
    print(f"  Case 2: Meridian Holdings — Layering (5 transactions, 3 triggers)")
    print("═" * 50)


if __name__ == "__main__":
    asyncio.run(seed())
