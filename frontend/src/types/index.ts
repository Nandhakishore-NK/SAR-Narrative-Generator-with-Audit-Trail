/**
 * SAR Guardian — TypeScript Type Definitions
 * Mirrors backend Pydantic schemas for type safety.
 */

// ===== Auth =====
export interface User {
  id: string;
  name: string;
  email: string;
  role: "analyst" | "supervisor" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

// ===== Cases =====
export interface Case {
  id: string;
  customer_id: string;
  customer_name: string;
  customer_type?: string;
  customer_risk_rating?: string;
  kyc_id_type?: string;
  kyc_id_number?: string;
  kyc_country?: string;
  kyc_occupation?: string;
  kyc_onboarding_date?: string;
  account_number?: string;
  account_type?: string;
  account_open_date?: string;
  account_balance?: number;
  account_currency?: string;
  alert_id?: string;
  alert_date?: string;
  alert_type?: string;
  alert_score?: number;
  status: string;
  notes?: string;
  historical_avg_monthly_volume?: number;
  historical_avg_transaction_size?: number;
  historical_counterparty_count?: number;
  historical_sar_count?: number;
  composite_risk_score?: number;
  network_risk_score?: number;
  behavioral_risk_score?: number;
  graph_analysis?: string;
  overall_risk_score?: number;
  alert_typology?: string;
  // UI-referenced fields (mapped from backend equivalents)
  kyc_status?: string;
  pep_status?: boolean;
  jurisdiction?: string;
  occupation?: string;
  alert_triggered_date?: string;
  prior_sar_count?: number;
  graph_connections_count?: number;
  case_narrative_summary?: string;
  created_at: string;
  updated_at: string;
}

export interface CaseListItem {
  id: string;
  customer_id: string;
  customer_name: string;
  customer_risk_rating?: string;
  alert_id?: string;
  alert_type?: string;
  status: string;
  composite_risk_score?: number;
  created_at: string;
}

// ===== Transactions =====
export interface Transaction {
  id: string;
  case_id: string;
  transaction_ref?: string;
  amount: number;
  currency: string;
  transaction_date: string;
  transaction_type?: string;
  direction?: string;
  counterparty_name?: string;
  counterparty_account?: string;
  counterparty_bank?: string;
  country?: string;
  // Alias referenced in some UI components
  counterparty_country?: string;
  purpose?: string;
  is_flagged: boolean;
  created_at: string;
}

// ===== Rule Triggers =====
export interface RuleTrigger {
  id: string;
  case_id: string;
  rule_code: string;
  rule_description?: string;
  threshold_value?: number;
  actual_value?: number;
  breached: boolean;
  typology_code?: string;
  typology_description?: string;
  created_at: string;
}

// ===== SAR Narrative =====
export interface SentenceBreakdown {
  id?: string;
  sentence_id: string;
  sentence_index: number;
  sentence_text: string;
  sentence_hash: string;
  confidence_level: "LOW" | "MEDIUM" | "HIGH";
  supporting_transaction_ids: string[];
  rule_reference?: string;
  threshold_reference?: string;
  typology_reference?: string;
  graph_reference?: string;
  evidence_source?: string;
}

export interface SarNarrative {
  narrative_id: string;
  case_id: string;
  narrative_text: string;
  version: number;
  severity: string;
  is_active: boolean;
  created_by: string;
  created_at: string;
  sentences: SentenceBreakdown[];
}

// NarrativeSentence is an alias for SentenceBreakdown
export type NarrativeSentence = SentenceBreakdown;

// ===== Audit Trail =====
export interface AuditTrail {
  id: string;
  case_id: string;
  audit_json: Record<string, any>;
  model_version: string;
  narrative_version: number;
  timestamp: string;
}

export interface AuditTimelineEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  actor_id?: string;
  details?: string;
  hash_signature: string;
  previous_hash?: string;
  timestamp: string;
}

export interface AuditTimeline {
  case_id: string;
  entries: AuditTimelineEntry[];
  chain_valid: boolean;
}

// ===== Overrides =====
export interface Override {
  id: string;
  sentence_id: string;
  original_hash: string;
  modified_text: string;
  modified_hash: string;
  override_reason_code: string;
  evidence_reference: string;
  analyst_id: string;
  supervisor_id?: string;
  approval_status: "pending" | "approved" | "rejected";
  approval_notes?: string;
  created_at: string;
  updated_at: string;
}

export type OverrideReasonCode =
  | "factual_correction"
  | "additional_evidence"
  | "regulatory_update"
  | "typology_reclassification"
  | "risk_reassessment"
  | "data_quality_issue"
  | "supervisor_directed";
