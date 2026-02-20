"""
Sample Data Generator and Data Processor for SAR System.
Provides realistic synthetic data for demo and testing.
"""
import random
import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# IST = UTC + 5:30
_IST = timezone(timedelta(hours=5, minutes=30))

def ist_now() -> datetime:
    """Return current datetime in IST."""
    return datetime.now(_IST)

def to_ist(dt: datetime) -> datetime:
    """Convert a naive UTC datetime (from DB) to IST for display."""
    if dt is None:
        return dt
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_IST)
from app.models.database import (
    CustomerProfile, TransactionAlert, SARCase, SessionLocal,
    AlertSeverity, CaseStatus
)

SAMPLE_CUSTOMERS = [
    {
        "customer_id": "CUST-001",
        "full_name": "Arjun Sharma",
        "date_of_birth": "1985-03-15",
        "nationality": "Indian",
        "id_type": "Passport",
        "id_number": "P12345678",
        "address": "45, Brigade Road, Bengaluru, Karnataka - 560001",
        "occupation": "Import/Export Trader",
        "employer": "Sharma Trading Pvt Ltd",
        "annual_income": 8500000.0,
        "risk_rating": "HIGH",
        "kyc_status": "VERIFIED",
        "kyc_date": "2023-01-10",
        "pep_status": False,
        "sanctions_checked": True,
        "account_opening_date": "2021-06-15",
        "phone": "+91 98450 12345",
        "email": "a.sharma@sharmatrading.in",
        "country": "India"
    },
    {
        "customer_id": "CUST-002",
        "full_name": "Ravi Krishnamurthy",
        "date_of_birth": "1978-07-22",
        "nationality": "Indian",
        "id_type": "Aadhaar",
        "id_number": "4567-8901-2345",
        "address": "12, Banjara Hills, Road No. 2, Hyderabad, Telangana - 500034",
        "occupation": "Real Estate Developer",
        "employer": "Krishnamurthy Realty Ltd",
        "annual_income": 25000000.0,
        "risk_rating": "VERY HIGH",
        "kyc_status": "ENHANCED_DUE_DILIGENCE",
        "kyc_date": "2023-03-22",
        "pep_status": True,
        "sanctions_checked": True,
        "account_opening_date": "2020-11-01",
        "phone": "+91 99890 56789",
        "email": "r.krishnamurthy@krrealty.in",
        "country": "India"
    },
    {
        "customer_id": "CUST-003",
        "full_name": "Mohammed Al-Rashid",
        "date_of_birth": "1990-12-04",
        "nationality": "UAE",
        "id_type": "Passport",
        "id_number": "UAE654321",
        "address": "78, Linking Road, Bandra West, Mumbai, Maharashtra - 400050",
        "occupation": "Financial Consultant",
        "employer": "Self-Employed",
        "annual_income": 12000000.0,
        "risk_rating": "HIGH",
        "kyc_status": "VERIFIED",
        "kyc_date": "2023-05-15",
        "pep_status": False,
        "sanctions_checked": True,
        "account_opening_date": "2022-02-20",
        "phone": "+91 98200 78901",
        "email": "m.alrashid@gmail.com",
        "country": "India"
    },
    {
        "customer_id": "CUST-004",
        "full_name": "Priya Venkatesh",
        "date_of_birth": "1999-08-30",
        "nationality": "Indian",
        "id_type": "Aadhaar",
        "id_number": "7890-1234-5678",
        "address": "33, Velachery Main Road, Chennai, Tamil Nadu - 600042",
        "occupation": "Student",
        "employer": "N/A",
        "annual_income": 120000.0,
        "risk_rating": "MEDIUM",
        "kyc_status": "VERIFIED",
        "kyc_date": "2023-09-01",
        "pep_status": False,
        "sanctions_checked": True,
        "account_opening_date": "2023-09-01",
        "phone": "+91 90000 12345",
        "email": "priya.venkatesh@student.edu.in",
        "country": "India"
    },
    {
        "customer_id": "CUST-005",
        "full_name": "Sunita Agarwal",
        "date_of_birth": "1972-05-18",
        "nationality": "Indian",
        "id_type": "PAN",
        "id_number": "ABCPA1234Z",
        "address": "56, Lajpat Nagar II, New Delhi - 110024",
        "occupation": "Retail Business Owner",
        "employer": "Agarwal Traders Pvt Ltd",
        "annual_income": 6500000.0,
        "risk_rating": "HIGH",
        "kyc_status": "VERIFIED",
        "kyc_date": "2022-11-20",
        "pep_status": False,
        "sanctions_checked": True,
        "account_opening_date": "2019-04-12",
        "phone": "+91 98110 34567",
        "email": "s.agarwal@agarwaltraders.in",
        "country": "India"
    }
]

SAMPLE_ALERTS = [
    {
        "alert_id": "ALT-2024-001",
        "customer_id": "CUST-001",
        "alert_type": "STRUCTURING",
        "alert_rule": "CASH_STRUCTURING_RULE_001",
        "severity": "HIGH",
        "total_amount": 48750000.0,
        "transaction_count": 47,
        "date_range_start": "2024-01-08",
        "date_range_end": "2024-01-15",
        "counterparties": [f"ACC-{str(i).zfill(4)}" for i in range(1, 48)],
        "jurisdictions_involved": ["India", "United Arab Emirates", "Hong Kong", "Cayman Islands"],
        "alert_score": 94.5,
        "triggering_factors": [
            "47 incoming transfers from different source accounts in 7 days",
            "Immediate outbound international wire transfer of ₹4,85,00,000 following receipt",
            "Transaction amounts structured at ₹9,00,000–₹9,99,999 range — structured to avoid RBI CTR threshold of ₹10,00,000",
            "Destination account in UAE - FATF high-risk jurisdiction",
            "Activity inconsistent with stated occupation (Import/Export Trader) and annual income (₹85,00,000)"
        ]
    },
    {
        "alert_id": "ALT-2024-002",
        "customer_id": "CUST-002",
        "alert_type": "HIGH_RISK_JURISDICTION",
        "alert_rule": "INTL_WIRE_HIGH_RISK_004",
        "severity": "CRITICAL",
        "total_amount": 210000000.0,
        "transaction_count": 8,
        "date_range_start": "2024-02-01",
        "date_range_end": "2024-02-28",
        "counterparties": ["Krishnamurthy Holdings BVI", "Cayman Trust Co", "Cyprus Asset Management", "Dubai RE LLC"],
        "jurisdictions_involved": ["India", "British Virgin Islands", "Cyprus", "United Arab Emirates"],
        "alert_score": 98.2,
        "triggering_factors": [
            "PEP customer transferring ₹21,00,00,000 to high-risk jurisdictions in one month",
            "Funds routed through multiple offshore shell companies — classic layering under PMLA",
            "No credible commercial explanation provided for transfers despite bank enquiry",
            "Pattern consistent with Round-tripping and money laundering through real estate",
            "BVI and Cyprus shell companies identified as beneficiaries — FATF red flag"
        ]
    },
    {
        "alert_id": "ALT-2024-003",
        "customer_id": "CUST-003",
        "alert_type": "RAPID_MOVEMENT",
        "alert_rule": "PASS_THROUGH_RULE_007",
        "severity": "HIGH",
        "total_amount": 35000000.0,
        "transaction_count": 23,
        "date_range_start": "2024-03-10",
        "date_range_end": "2024-03-25",
        "counterparties": ["Various Indian Businesses", "Personal Account UAE", "Crypto Exchange A"],
        "jurisdictions_involved": ["India", "United Arab Emirates"],
        "alert_score": 87.3,
        "triggering_factors": [
            "Rapid in-out movement: ₹3,50,00,000 received and transferred out within 24-48 hours",
            "Payments to unregulated cryptocurrency exchange — non-compliant under RBI Virtual Currency guidelines",
            "23 transactions in 15 days with no apparent business purpose declared",
            "Customer unable to provide satisfactory explanation during bank enquiry",
            "Partial conversion to cryptocurrency detected — potential layering vehicle"
        ]
    },
    {
        "alert_id": "ALT-2024-004",
        "customer_id": "CUST-004",
        "alert_type": "MULE_ACCOUNT",
        "alert_rule": "MULE_DETECTION_RULE_012",
        "severity": "CRITICAL",
        "total_amount": 9850000.0,
        "transaction_count": 12,
        "date_range_start": "2024-04-01",
        "date_range_end": "2024-04-05",
        "counterparties": ["Unknown Individual", "Crypto Exchange B", "Cash ATM Withdrawals"],
        "jurisdictions_involved": ["India"],
        "alert_score": 96.1,
        "triggering_factors": [
            "Student account with stated annual income of ₹1,20,000 received ₹98,50,000 in 5 days — 82x income",
            "Account opened only 7 months ago — recently opened account (mule recruitment indicator)",
            "Immediate cash ATM withdrawals and crypto conversions after receipt — layering pattern",
            "Funds originate from multiple victims of suspected UPI payment fraud",
            "Customer reportedly contacted via social media with 'investment opportunity' — classic mule recruitment under PMLA"
        ]
    },
    {
        "alert_id": "ALT-2024-005",
        "customer_id": "CUST-005",
        "alert_type": "TRADE_BASED_ML",
        "alert_rule": "TBML_INVOICE_RULE_003",
        "severity": "MEDIUM",
        "total_amount": 21500000.0,
        "transaction_count": 15,
        "date_range_start": "2024-05-01",
        "date_range_end": "2024-05-31",
        "counterparties": ["Dubai Wholesale FZE", "Colombo Imports Pvt Ltd", "Karachi Trading Co"],
        "jurisdictions_involved": ["India", "United Arab Emirates", "Pakistan", "Sri Lanka"],
        "alert_score": 73.8,
        "triggering_factors": [
            "Invoice discrepancies: goods valued 340% above market rate across 6 invoices — over-invoicing suspected",
            "Multiple NEFT payments referencing identical invoice numbers — duplicate payment fraud indicator",
            "Counterparty in Pakistan — FATF grey-listed jurisdiction per RBI advisory",
            "Import goods category (electronics) inconsistent with registered GST business activity (textiles)",
            "Payment routes: India → UAE → Pakistan rather than direct bilateral — classic TBML layering"
        ]
    }
]

SAMPLE_TRANSACTIONS_TEMPLATE = {
    "ALT-2024-001": [
        {"date": f"2024-01-{str(d).zfill(2)}", "amount": random.uniform(900000, 999999),
         "type": "CREDIT", "counterparty": f"Individual ACC-{str(i).zfill(4)}",
         "reference": f"REF-{uuid.uuid4().hex[:8].upper()}",
         "description": "Transfer from individual"}
        for i, d in enumerate(
            [8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 11, 11, 11, 11, 12, 12, 12, 12, 12,
             13, 13, 13, 14, 14, 14, 14, 14, 15, 15, 15], 1
        )
    ]
}


def generate_transactions_for_alert(alert: Dict) -> List[Dict]:
    """Generate realistic transaction records for a given alert."""
    transactions = []
    start = datetime.strptime(str(alert.get("date_range_start", "2024-01-01")), "%Y-%m-%d")
    end = datetime.strptime(str(alert.get("date_range_end", "2024-01-31")), "%Y-%m-%d")
    total = alert.get("total_amount", 100000)
    count = alert.get("transaction_count", 10)
    counterparties = alert.get("counterparties", ["Unknown"])
    alert_type = alert.get("alert_type", "UNKNOWN")
    days_range = max((end - start).days, 1)
    per_tx = total / count

    for i in range(count):
        tx_date = start + timedelta(days=random.randint(0, days_range))
        tx_amount = per_tx * random.uniform(0.85, 1.15)
        if alert_type == "STRUCTURING":
            tx_amount = random.uniform(900000, 999999)  # Just below RBI CTR threshold of ₹10,00,000
        txn = {
            "transaction_id": f"TXN-{uuid.uuid4().hex[:10].upper()}",
            "date": tx_date.strftime("%Y-%m-%d"),
            "time": f"{random.randint(8, 20):02d}:{random.randint(0, 59):02d}",
            "amount": round(tx_amount, 2),
            "currency": "INR",
            "type": "CREDIT" if i < count * 0.6 else "DEBIT",
            "counterparty": counterparties[i % len(counterparties)] if counterparties else "Unknown",
            "reference": f"REF-{uuid.uuid4().hex[:8].upper()}",
            "description": f"{alert_type.replace('_', ' ').title()} transaction #{i+1}",
            "channel": random.choice(["ONLINE_BANKING", "MOBILE_APP", "BRANCH", "ATM"]),
            "country": random.choice(alert.get("jurisdictions_involved", ["United Kingdom"]))
        }
        transactions.append(txn)
    transactions.sort(key=lambda x: x["date"])
    return transactions


def seed_sample_data():
    """Seed all sample data into the database."""
    db = SessionLocal()
    try:
        existing_customers = db.query(CustomerProfile).count()
        if existing_customers > 0:
            return
        # Insert customers
        for c in SAMPLE_CUSTOMERS:
            kyc_date = datetime.strptime(c["kyc_date"], "%Y-%m-%d") if c.get("kyc_date") else None
            open_date = datetime.strptime(c["account_opening_date"], "%Y-%m-%d") if c.get("account_opening_date") else None
            customer = CustomerProfile(
                customer_id=c["customer_id"],
                full_name=c["full_name"],
                date_of_birth=c["date_of_birth"],
                nationality=c["nationality"],
                id_type=c["id_type"],
                id_number=c["id_number"],
                address=c["address"],
                occupation=c["occupation"],
                employer=c["employer"],
                annual_income=c["annual_income"],
                risk_rating=c["risk_rating"],
                kyc_status=c["kyc_status"],
                kyc_date=kyc_date,
                pep_status=c["pep_status"],
                sanctions_checked=c["sanctions_checked"],
                account_opening_date=open_date,
                phone=c["phone"],
                email=c["email"],
                country=c["country"],
                created_at=datetime.utcnow()
            )
            db.add(customer)
        db.commit()
        # Insert alerts
        for a in SAMPLE_ALERTS:
            alert = TransactionAlert(
                alert_id=a["alert_id"],
                customer_id=a["customer_id"],
                alert_type=a["alert_type"],
                alert_rule=a["alert_rule"],
                severity=AlertSeverity(a["severity"]),
                transaction_data=generate_transactions_for_alert(a),
                total_amount=a["total_amount"],
                transaction_count=a["transaction_count"],
                date_range_start=datetime.strptime(str(a["date_range_start"]), "%Y-%m-%d"),
                date_range_end=datetime.strptime(str(a["date_range_end"]), "%Y-%m-%d"),
                counterparties=a["counterparties"],
                jurisdictions_involved=a["jurisdictions_involved"],
                alert_score=a["alert_score"],
                triggering_factors=a["triggering_factors"],
                status="OPEN",
                created_at=datetime.utcnow()
            )
            db.add(alert)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Sample data seed error: {e}")
    finally:
        db.close()


def get_customer_dict(customer: CustomerProfile) -> Dict:
    """Convert CustomerProfile to dict for LLM context."""
    return {
        "customer_id": customer.customer_id,
        "full_name": customer.full_name,
        "date_of_birth": customer.date_of_birth,
        "nationality": customer.nationality,
        "id_type": customer.id_type,
        "id_number": customer.id_number,
        "address": customer.address,
        "occupation": customer.occupation,
        "employer": customer.employer,
        "annual_income": customer.annual_income,
        "risk_rating": customer.risk_rating,
        "kyc_status": customer.kyc_status,
        "kyc_date": str(customer.kyc_date) if customer.kyc_date else None,
        "pep_status": customer.pep_status,
        "sanctions_checked": customer.sanctions_checked,
        "account_opening_date": str(customer.account_opening_date) if customer.account_opening_date else None,
        "country": customer.country
    }


def get_alert_dict(alert: TransactionAlert) -> Dict:
    """Convert TransactionAlert to dict for LLM context."""
    return {
        "alert_id": alert.alert_id,
        "alert_type": alert.alert_type,
        "alert_rule": alert.alert_rule,
        "severity": alert.severity.value if hasattr(alert.severity, 'value') else alert.severity,
        "total_amount": alert.total_amount,
        "transaction_count": alert.transaction_count,
        "date_range_start": str(alert.date_range_start) if alert.date_range_start else None,
        "date_range_end": str(alert.date_range_end) if alert.date_range_end else None,
        "counterparties": alert.counterparties,
        "jurisdictions_involved": alert.jurisdictions_involved,
        "alert_score": alert.alert_score,
        "triggering_factors": alert.triggering_factors
    }


def format_inr(amount: float) -> str:
    """Format amount in Indian number system with ₹ prefix.

    Examples:
        2_10_00_000  -> ₹2.10 Cr
        98_50_000    -> ₹98.50 L
        45_000       -> ₹45,000
    """
    if amount is None:
        return "₹0"
    amount = float(amount)
    if amount >= 1_00_00_000:  # 1 crore
        return f"₹{amount / 1_00_00_000:.2f} Cr"
    elif amount >= 1_00_000:   # 1 lakh
        return f"₹{amount / 1_00_000:.2f} L"
    else:
        # Indian comma formatting: last 3 digits, then groups of 2
        s = str(int(amount))
        if len(s) <= 3:
            return f"₹{s}"
        result = s[-3:]
        s = s[:-3]
        while len(s) > 2:
            result = s[-2:] + "," + result
            s = s[:-2]
        result = (s + "," + result) if s else result
        return f"₹{result}"
