/**
 * Case detail page — /cases/[id]
 * Full case view: customer info, transactions, rule triggers,
 * SAR narrative with sentence-level breakdown, override governance, audit link.
 */

"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { OverrideModal } from "@/components/override-modal";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  formatDate,
  formatCurrency,
  severityColor,
  statusBadge,
  confidenceColor,
} from "@/lib/utils";
import {
  ArrowLeft,
  FileText,
  Shield,
  History,
  AlertTriangle,
  Pencil,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import type {
  Case,
  Transaction,
  RuleTrigger,
  SarNarrative,
  NarrativeSentence,
  Override,
} from "@/types";

export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [caseData, setCaseData] = useState<Case | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [ruleTriggers, setRuleTriggers] = useState<RuleTrigger[]>([]);
  const [narrative, setNarrative] = useState<SarNarrative | null>(null);
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  // Override modal state
  const [overrideOpen, setOverrideOpen] = useState(false);
  const [selectedSentence, setSelectedSentence] =
    useState<NarrativeSentence | null>(null);

  // Override approvals
  const [pendingOverrides, setPendingOverrides] = useState<Override[]>([]);

  useEffect(() => {
    loadAllData();
  }, [id]);

  const loadAllData = useCallback(async () => {
    setLoading(true);
    try {
      const [caseRes, txRes, rulesRes] = await Promise.all([
        api.get(`/cases/${id}`),
        api.get(`/cases/${id}/transactions`),
        api.get(`/cases/${id}/rule-triggers`),
      ]);
      setCaseData(caseRes.data);
      setTransactions(txRes.data);
      setRuleTriggers(rulesRes.data);

      // Try to load existing narrative
      try {
        const narRes = await api.get(`/sar/cases/${id}/narrative`);
        setNarrative(narRes.data);
      } catch {
        setNarrative(null);
      }

      // Load pending overrides
      try {
        const ovRes = await api.get("/overrides/pending");
        setPendingOverrides(ovRes.data);
      } catch {
        setPendingOverrides([]);
      }
    } catch (err) {
      console.error("Failed to load case data", err);
    } finally {
      setLoading(false);
    }
  }, [id]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.post("/sar/generate", { case_id: id });
      setNarrative(res.data);
      // Refresh case status
      const caseRes = await api.get(`/cases/${id}`);
      setCaseData(caseRes.data);
    } catch (err) {
      console.error("SAR generation failed", err);
    } finally {
      setGenerating(false);
    }
  };

  const handleOverrideClick = (sentence: NarrativeSentence) => {
    setSelectedSentence(sentence);
    setOverrideOpen(true);
  };

  const handleOverrideSuccess = () => {
    loadAllData();
  };

  const handleApproveOverride = async (overrideId: string, approve: boolean) => {
    try {
      await api.patch(`/overrides/${overrideId}/approve`, {
        approved: approve,
        reviewer_notes: approve ? "Approved" : "Rejected",
      });
      loadAllData();
    } catch (err) {
      console.error("Override approval failed", err);
    }
  };

  if (loading) {
    return (
      <>
        <Navbar />
        <div className="flex items-center justify-center min-h-[60vh]">
          <Spinner size="lg" />
        </div>
      </>
    );
  }

  if (!caseData) {
    return (
      <>
        <Navbar />
        <div className="container mx-auto px-4 md:px-6 py-8">
          <p className="text-muted-foreground">Case not found.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 md:px-6 py-8 space-y-6">
        {/* Back + Title */}
        <div className="flex items-center gap-4">
          <Link href="/cases">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold tracking-tight">
              {caseData.customer_name || `Case ${id?.slice(0, 8)}`}
            </h1>
            <p className="text-sm text-muted-foreground">
              Case ID: {id}
            </p>
          </div>
          <Badge variant={statusBadge(caseData.status) as any} className="capitalize text-sm">
            {caseData.status.replace("_", " ")}
          </Badge>
        </div>

        {/* Customer & Case Summary */}
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Customer Profile</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-y-3 gap-x-6 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Customer ID</p>
                <p className="font-medium">{caseData.customer_id || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Customer Type</p>
                <p className="font-medium capitalize">{caseData.customer_type || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Account Type</p>
                <p className="font-medium">{caseData.account_type || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Account Open Date</p>
                <p className="font-medium">
                  {caseData.account_open_date
                    ? formatDate(caseData.account_open_date)
                    : "—"}
                </p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">KYC Status</p>
                <p className="font-medium capitalize">{caseData.kyc_status || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">PEP Status</p>
                <Badge variant={caseData.pep_status ? "destructive" : "secondary"}>
                  {caseData.pep_status ? "Yes" : "No"}
                </Badge>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Jurisdiction</p>
                <p className="font-medium">{caseData.jurisdiction || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Occupation</p>
                <p className="font-medium">{caseData.occupation || "—"}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Risk Assessment</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Overall Risk Score</span>
                <span
                  className={`text-2xl font-bold ${severityColor(
                    (caseData.overall_risk_score ?? 0) >= 75
                      ? "critical"
                      : (caseData.overall_risk_score ?? 0) >= 50
                      ? "high"
                      : (caseData.overall_risk_score ?? 0) >= 25
                      ? "medium"
                      : "low"
                  )}`}
                >
                  {caseData.overall_risk_score ?? "N/A"}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground text-xs">Alert Typology</p>
                  <p className="font-medium">{caseData.alert_typology || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Alert Date</p>
                  <p className="font-medium">
                    {caseData.alert_triggered_date
                      ? formatDate(caseData.alert_triggered_date)
                      : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Prior SARs</p>
                  <p className="font-medium">{caseData.prior_sar_count ?? 0}</p>
                </div>
                <div>
                  <p className="text-muted-foreground text-xs">Graph Connections</p>
                  <p className="font-medium">
                    {caseData.graph_connections_count ?? 0} entities
                  </p>
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <Link href={`/audit-view/${id}`}>
                  <Button variant="outline" size="sm" className="gap-1">
                    <History className="h-3 w-3" />
                    Audit Trail
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Transactions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Transactions ({transactions.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {transactions.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">
                No transactions recorded.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Direction</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead className="hidden md:table-cell">Counterparty</TableHead>
                    <TableHead className="hidden lg:table-cell">Country</TableHead>
                    <TableHead>Flagged</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((tx) => (
                    <TableRow key={tx.id}>
                      <TableCell className="text-sm">
                        {formatDate(tx.transaction_date)}
                      </TableCell>
                      <TableCell className="capitalize text-sm">
                        {tx.transaction_type}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={tx.direction === "inbound" ? "info" : "warning"}
                          className="capitalize"
                        >
                          {tx.direction}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatCurrency(tx.amount, tx.currency)}
                      </TableCell>
                      <TableCell className="hidden md:table-cell text-sm">
                        {tx.counterparty_name || "—"}
                      </TableCell>
                      <TableCell className="hidden lg:table-cell text-sm">
                        {tx.counterparty_country || "—"}
                      </TableCell>
                      <TableCell>
                        {tx.is_flagged ? (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        ) : (
                          <span className="text-muted-foreground text-xs">No</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Rule Triggers */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">
              Rule Triggers ({ruleTriggers.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {ruleTriggers.length === 0 ? (
              <p className="p-6 text-sm text-muted-foreground">
                No rule triggers recorded.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rule Code</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-right">Threshold</TableHead>
                    <TableHead className="text-right">Actual</TableHead>
                    <TableHead>Breached</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {ruleTriggers.map((rt) => (
                    <TableRow key={rt.id}>
                      <TableCell className="font-mono text-sm font-medium">
                        {rt.rule_code}
                      </TableCell>
                      <TableCell className="text-sm">
                        {rt.rule_description || "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {rt.threshold_value?.toLocaleString() ?? "—"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {rt.actual_value?.toLocaleString() ?? "—"}
                      </TableCell>
                      <TableCell>
                        {rt.breached ? (
                          <Badge variant="destructive">Breached</Badge>
                        ) : (
                          <Badge variant="secondary">Within</Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* SAR Narrative Section */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileText className="h-5 w-5" />
                SAR Narrative
              </CardTitle>
              {narrative && (
                <CardDescription>
                  Version {narrative.version} | Severity:{" "}
                  <span
                    className={`font-semibold ${severityColor(
                      narrative.severity || "medium"
                    )}`}
                  >
                    {narrative.severity}
                  </span>{" "}
                  | Generated {formatDate(narrative.created_at)}
                </CardDescription>
              )}
            </div>
            <div className="flex gap-2">
              {
                <Button
                  onClick={handleGenerate}
                  disabled={generating}
                  className="gap-2"
                >
                  {generating ? (
                    <>
                      <Spinner size="sm" className="text-primary-foreground" />
                      Generating…
                    </>
                  ) : (
                    <>
                      <Shield className="h-4 w-4" />
                      {narrative ? "Regenerate" : "Generate SAR"}
                    </>
                  )}
                </Button>
              }
            </div>
          </CardHeader>
          <CardContent>
            {!narrative ? (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 opacity-30" />
                <p>No SAR narrative generated yet.</p>
                <p className="text-sm mt-1">
                  Click &quot;Generate SAR&quot; to create a regulator-grade narrative.
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Full narrative text */}
                <div className="rounded-lg bg-muted/50 p-4 text-sm leading-relaxed whitespace-pre-wrap border">
                  {narrative.narrative_text}
                </div>

                {/* Sentence-level breakdown */}
                {narrative.sentences && narrative.sentences.length > 0 && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
                      Sentence-Level Breakdown
                    </h3>
                    {narrative.sentences.map((s, idx) => (
                      <div
                        key={s.id}
                        className="rounded-lg border p-4 space-y-2 hover:shadow-sm transition-shadow"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 space-y-1">
                            <p className="text-sm">{s.sentence_text}</p>
                            <div className="flex items-center gap-3 text-xs text-muted-foreground">
                              <span>
                                Confidence:{" "}
                                <Badge
                                  variant={
                                    confidenceColor(
                                      s.confidence_level || "medium"
                                    ) as any
                                  }
                                  className="text-[10px]"
                                >
                                  {s.confidence_level}
                                </Badge>
                              </span>
                              <span className="font-mono text-[10px]">
                                #{s.sentence_hash?.slice(0, 12)}…
                              </span>
                              {s.evidence_source && (
                                <span>Source: {s.evidence_source}</span>
                              )}
                            </div>
                          </div>
                          <Button
                              variant="ghost"
                              size="sm"
                              className="gap-1 flex-shrink-0"
                              onClick={() => handleOverrideClick(s)}
                            >
                              <Pencil className="h-3 w-3" />
                              Override
                            </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Pending Overrides (Supervisor View) */}
        {pendingOverrides.length > 0 && (
            <Card className="border-amber-200">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2 text-amber-700">
                  <Clock className="h-5 w-5" />
                  Pending Override Approvals
                </CardTitle>
                <CardDescription>
                  Review and approve/reject analyst override requests.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {pendingOverrides.map((ov) => (
                  <div
                    key={ov.id}
                    className="rounded-lg border border-amber-100 p-4 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <Badge variant="warning" className="capitalize">
                        {ov.override_reason_code?.replace("_", " ")}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(ov.created_at)}
                      </span>
                    </div>
                    <div className="grid gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground text-xs">
                          Original Hash:
                        </span>
                        <p className="font-mono text-xs">{ov.original_hash}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground text-xs">
                          Modified Hash:
                        </span>
                        <p className="font-mono text-xs">{ov.modified_hash}</p>
                      </div>
                      {ov.evidence_reference && (
                        <div>
                          <span className="text-muted-foreground text-xs">
                            Evidence:
                          </span>
                          <p className="text-sm">{ov.evidence_reference}</p>
                        </div>
                      )}
                    </div>
                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        className="gap-1"
                        onClick={() => handleApproveOverride(ov.id, true)}
                      >
                        <CheckCircle className="h-3 w-3" />
                        Approve
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        className="gap-1"
                        onClick={() => handleApproveOverride(ov.id, false)}
                      >
                        <XCircle className="h-3 w-3" />
                        Reject
                      </Button>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
      </main>

      {/* Override Modal */}
      <OverrideModal
        sentence={selectedSentence}
        open={overrideOpen}
        onOpenChange={setOverrideOpen}
        onSuccess={handleOverrideSuccess}
      />
    </>
  );
}
