/**
 * Audit View page — /audit-view/[id]
 * Structured JSON view, hash verification, change history timeline, override log.
 */

"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Navbar } from "@/components/navbar";
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
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft,
  ShieldCheck,
  ShieldAlert,
  Clock,
  Hash,
  FileJson,
  CheckCircle2,
  XCircle,
  Link2,
} from "lucide-react";

interface TimelineEntry {
  id: string;
  entity_type: string;
  entity_id: string;
  action: string;
  previous_hash: string | null;
  hash_signature: string;
  timestamp: string;
}

interface AuditData {
  case_id: string;
  audit_json: Record<string, any>;
  model_version: string | null;
  narrative_version: number | null;
  created_at: string;
}

export default function AuditViewPage() {
  const { id } = useParams<{ id: string }>();
  const { user, token } = useAuth();
  const router = useRouter();

  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [chainValid, setChainValid] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    fetchAuditData();
  }, [token, id]);

  const fetchAuditData = async () => {
    setLoading(true);
    try {
      // Fetch timeline with chain verification
      const timelineRes = await api.get(`/audit/${id}/timeline`);
      const data = timelineRes.data;
      setTimeline(data.entries || []);
      setChainValid(data.chain_valid ?? null);

      // Fetch audit trail data
      try {
        const auditRes = await api.get(`/sar/cases/${id}/audit`);
        setAuditData(auditRes.data);
      } catch {
        setAuditData(null);
      }
    } catch (err) {
      console.error("Failed to fetch audit data", err);
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

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

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 md:px-6 py-8 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link href={`/cases/${id}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex-1">
            <h1 className="text-2xl font-bold tracking-tight">
              Immutable Audit Trail
            </h1>
            <p className="text-sm text-muted-foreground">Case ID: {id}</p>
          </div>
        </div>

        {/* Hash Chain Verification */}
        <Card
          className={
            chainValid === true
              ? "border-emerald-200"
              : chainValid === false
              ? "border-red-200"
              : ""
          }
        >
          <CardHeader className="flex flex-row items-center gap-3">
            {chainValid === true ? (
              <ShieldCheck className="h-8 w-8 text-emerald-600" />
            ) : chainValid === false ? (
              <ShieldAlert className="h-8 w-8 text-red-600" />
            ) : (
              <Hash className="h-8 w-8 text-muted-foreground" />
            )}
            <div>
              <CardTitle className="text-lg">
                Hash Chain Integrity
              </CardTitle>
              <CardDescription>
                {chainValid === true
                  ? "All hash signatures verified. Chain is intact and untampered."
                  : chainValid === false
                  ? "INTEGRITY VIOLATION DETECTED — Hash chain has been broken."
                  : "Chain verification status unavailable."}
              </CardDescription>
            </div>
            <Badge
              variant={
                chainValid === true
                  ? "success"
                  : chainValid === false
                  ? "destructive"
                  : "secondary"
              }
              className="ml-auto text-sm"
            >
              {chainValid === true
                ? "VERIFIED"
                : chainValid === false
                ? "BROKEN"
                : "UNKNOWN"}
            </Badge>
          </CardHeader>
        </Card>

        {/* Audit JSON */}
        {auditData && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <FileJson className="h-5 w-5" />
                Audit Snapshot (JSON)
              </CardTitle>
              <CardDescription>
                {auditData.model_version && (
                  <span>Model: {auditData.model_version} | </span>
                )}
                {auditData.narrative_version != null && (
                  <span>Narrative v{auditData.narrative_version} | </span>
                )}
                Captured {formatDate(auditData.created_at)}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="rounded-lg bg-slate-950 text-slate-50 p-4 text-xs font-mono overflow-auto max-h-[500px] leading-relaxed">
                {JSON.stringify(auditData.audit_json, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Timeline */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Event Timeline ({timeline.length} entries)
            </CardTitle>
            <CardDescription>
              Append-only immutable log. Each entry&apos;s hash incorporates the previous
              entry&apos;s hash (blockchain-style chain).
            </CardDescription>
          </CardHeader>
          <CardContent>
            {timeline.length === 0 ? (
              <p className="text-sm text-muted-foreground py-8 text-center">
                No audit events recorded for this case.
              </p>
            ) : (
              <div className="relative pl-6 space-y-0">
                {/* Vertical line */}
                <div className="absolute left-[11px] top-2 bottom-2 w-0.5 bg-border" />

                {timeline.map((entry, idx) => {
                  const isFirst = idx === 0;
                  const isLast = idx === timeline.length - 1;

                  const actionColor =
                    entry.action.includes("generate") || entry.action.includes("create")
                      ? "text-emerald-600 bg-emerald-50"
                      : entry.action.includes("override") || entry.action.includes("modify")
                      ? "text-amber-600 bg-amber-50"
                      : entry.action.includes("approve")
                      ? "text-blue-600 bg-blue-50"
                      : entry.action.includes("reject")
                      ? "text-red-600 bg-red-50"
                      : "text-slate-600 bg-slate-50";

                  return (
                    <div key={entry.id} className="relative pb-6 last:pb-0">
                      {/* Dot */}
                      <div
                        className={`absolute -left-[13px] top-1 h-5 w-5 rounded-full border-2 border-background flex items-center justify-center ${actionColor}`}
                      >
                        <div className="h-2 w-2 rounded-full bg-current" />
                      </div>

                      <div className="ml-4 rounded-lg border p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="font-mono text-xs">
                              {entry.entity_type}
                            </Badge>
                            <span className="text-sm font-medium capitalize">
                              {entry.action.replace(/_/g, " ")}
                            </span>
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(entry.timestamp)}
                          </span>
                        </div>

                        <div className="grid gap-1.5 text-xs">
                          <div className="flex items-center gap-1">
                            <Hash className="h-3 w-3 text-muted-foreground" />
                            <span className="text-muted-foreground">Hash:</span>
                            <code className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                              {entry.hash_signature}
                            </code>
                          </div>
                          {entry.previous_hash && (
                            <div className="flex items-center gap-1">
                              <Link2 className="h-3 w-3 text-muted-foreground" />
                              <span className="text-muted-foreground">
                                Prev:
                              </span>
                              <code className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded">
                                {entry.previous_hash}
                              </code>
                            </div>
                          )}
                          <div className="flex items-center gap-1">
                            <span className="text-muted-foreground">
                              Entity ID:
                            </span>
                            <code className="font-mono text-[10px]">
                              {entry.entity_id}
                            </code>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Integrity Notice */}
        <div className="rounded-lg bg-muted/50 border p-4 text-center text-xs text-muted-foreground">
          <ShieldCheck className="h-4 w-4 inline-block mr-1 -mt-0.5" />
          This audit trail is append-only and uses SHA-256 hash chaining.
          Each entry&apos;s integrity is mathematically verifiable.
          Unauthorized modifications will break the chain.
        </div>
      </main>
    </>
  );
}
