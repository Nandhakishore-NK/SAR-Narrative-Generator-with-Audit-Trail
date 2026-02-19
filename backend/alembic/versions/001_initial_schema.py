"""001 — Initial Schema

Creates all core tables for SAR Guardian:
- users (with roles)
- cases (customer/alert/KYC/account data)
- transactions
- rule_triggers
- sar_narratives (versioned)
- narrative_sentences (hashed)
- audit_trails (JSONB)
- overrides (governance-controlled)
- immutable_logs (hash-chained)

Revision ID: 001
Create Date: 2026-02-19
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------- Enum Types -------
    user_role_enum = sa.Enum("analyst", "supervisor", "admin", name="user_role_enum")
    case_status_enum = sa.Enum("open", "under_review", "sar_generated", "escalated", "closed", name="case_status_enum")
    confidence_level_enum = sa.Enum("LOW", "MEDIUM", "HIGH", name="confidence_level_enum")
    approval_status_enum = sa.Enum("pending", "approved", "rejected", name="approval_status_enum")
    override_reason_code_enum = sa.Enum(
        "factual_correction", "additional_evidence", "regulatory_update",
        "typology_reclassification", "risk_reassessment", "data_quality_issue",
        "supervisor_directed", name="override_reason_code_enum"
    )

    # ------- Users -------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="analyst"),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ------- Cases -------
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_id", sa.String(100), nullable=False),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("customer_type", sa.String(50)),
        sa.Column("customer_risk_rating", sa.String(20)),
        sa.Column("kyc_id_type", sa.String(50)),
        sa.Column("kyc_id_number", sa.String(100)),
        sa.Column("kyc_country", sa.String(100)),
        sa.Column("kyc_occupation", sa.String(255)),
        sa.Column("kyc_onboarding_date", sa.DateTime(timezone=True)),
        sa.Column("account_number", sa.String(50)),
        sa.Column("account_type", sa.String(50)),
        sa.Column("account_open_date", sa.DateTime(timezone=True)),
        sa.Column("account_balance", sa.Float()),
        sa.Column("account_currency", sa.String(10), server_default="USD"),
        sa.Column("alert_id", sa.String(100)),
        sa.Column("alert_date", sa.DateTime(timezone=True)),
        sa.Column("alert_type", sa.String(100)),
        sa.Column("alert_score", sa.Float()),
        sa.Column("status", case_status_enum, nullable=False, server_default="open"),
        sa.Column("notes", sa.Text()),
        sa.Column("historical_avg_monthly_volume", sa.Float()),
        sa.Column("historical_avg_transaction_size", sa.Float()),
        sa.Column("historical_counterparty_count", sa.Integer()),
        sa.Column("historical_sar_count", sa.Integer(), server_default="0"),
        sa.Column("composite_risk_score", sa.Float()),
        sa.Column("network_risk_score", sa.Float()),
        sa.Column("behavioral_risk_score", sa.Float()),
        sa.Column("graph_analysis", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_cases_customer_id", "cases", ["customer_id"])
    op.create_index("ix_cases_alert_id", "cases", ["alert_id"])

    # ------- Transactions -------
    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transaction_ref", sa.String(100)),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="USD"),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("transaction_type", sa.String(50)),
        sa.Column("direction", sa.String(10)),
        sa.Column("counterparty_name", sa.String(255)),
        sa.Column("counterparty_account", sa.String(100)),
        sa.Column("counterparty_bank", sa.String(255)),
        sa.Column("country", sa.String(100)),
        sa.Column("purpose", sa.Text()),
        sa.Column("is_flagged", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_transactions_case_id", "transactions", ["case_id"])
    op.create_index("ix_transactions_ref", "transactions", ["transaction_ref"])

    # ------- Rule Triggers -------
    op.create_table(
        "rule_triggers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_code", sa.String(50), nullable=False),
        sa.Column("rule_description", sa.Text()),
        sa.Column("threshold_value", sa.Float()),
        sa.Column("actual_value", sa.Float()),
        sa.Column("breached", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("typology_code", sa.String(50)),
        sa.Column("typology_description", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_rule_triggers_case_id", "rule_triggers", ["case_id"])

    # ------- SAR Narratives -------
    op.create_table(
        "sar_narratives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("narrative_text", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sar_narratives_case_id", "sar_narratives", ["case_id"])

    # ------- Narrative Sentences -------
    op.create_table(
        "narrative_sentences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("narrative_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sar_narratives.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sentence_index", sa.Integer(), nullable=False),
        sa.Column("sentence_text", sa.Text(), nullable=False),
        sa.Column("sentence_hash", sa.String(64), nullable=False),
        sa.Column("confidence_level", confidence_level_enum, nullable=False, server_default="MEDIUM"),
        sa.Column("supporting_transaction_ids", sa.Text()),
        sa.Column("rule_reference", sa.String(100)),
        sa.Column("threshold_reference", sa.String(255)),
        sa.Column("typology_reference", sa.String(255)),
        sa.Column("graph_reference", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_narrative_sentences_narrative_id", "narrative_sentences", ["narrative_id"])

    # ------- Audit Trails -------
    op.create_table(
        "audit_trails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("audit_json", postgresql.JSONB(), nullable=False),
        sa.Column("model_version", sa.String(50), nullable=False),
        sa.Column("narrative_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_trails_case_id", "audit_trails", ["case_id"])

    # ------- Overrides -------
    op.create_table(
        "overrides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sentence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("narrative_sentences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_hash", sa.String(64), nullable=False),
        sa.Column("modified_text", sa.Text(), nullable=False),
        sa.Column("modified_hash", sa.String(64), nullable=False),
        sa.Column("override_reason_code", override_reason_code_enum, nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=False),
        sa.Column("analyst_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("supervisor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("approval_status", approval_status_enum, nullable=False, server_default="pending"),
        sa.Column("approval_notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_overrides_sentence_id", "overrides", ["sentence_id"])

    # ------- Immutable Logs (hash-chained) -------
    op.create_table(
        "immutable_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.String(100)),
        sa.Column("details", sa.Text()),
        sa.Column("previous_hash", sa.String(64)),
        sa.Column("hash_signature", sa.String(64), nullable=False, unique=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_immutable_logs_entity_type", "immutable_logs", ["entity_type"])
    op.create_index("ix_immutable_logs_entity_id", "immutable_logs", ["entity_id"])
    op.create_index("ix_immutable_logs_timestamp", "immutable_logs", ["timestamp"])


def downgrade() -> None:
    op.drop_table("immutable_logs")
    op.drop_table("overrides")
    op.drop_table("audit_trails")
    op.drop_table("narrative_sentences")
    op.drop_table("sar_narratives")
    op.drop_table("rule_triggers")
    op.drop_table("transactions")
    op.drop_table("cases")
    op.drop_table("users")

    # Drop enums
    sa.Enum(name="override_reason_code_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="approval_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="confidence_level_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="case_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
