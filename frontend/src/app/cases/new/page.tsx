/**
 * New Case page — /cases/new
 * Form to create a new SAR case with customer and alert details.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Spinner } from "@/components/ui/spinner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, AlertCircle, Save } from "lucide-react";

export default function NewCasePage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    customer_name: "",
    customer_id: "",
    customer_type: "individual",
    account_type: "",
    jurisdiction: "",
    occupation: "",
    kyc_status: "verified",
    pep_status: false,
    alert_typology: "",
    alert_triggered_date: "",
    overall_risk_score: "",
    case_narrative_summary: "",
  });

  const updateField = (field: string, value: any) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!form.customer_name.trim()) {
      setError("Customer name is required.");
      return;
    }

    setLoading(true);
    try {
      const payload = {
        ...form,
        overall_risk_score: form.overall_risk_score
          ? Number(form.overall_risk_score)
          : null,
        alert_triggered_date: form.alert_triggered_date || null,
      };
      const res = await api.post("/cases/", payload);
      router.push(`/cases/${res.data.id}`);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail || "Failed to create case.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!user) return null;

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 md:px-6 py-8 max-w-3xl space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Link href="/cases">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">New Case</h1>
            <p className="text-sm text-muted-foreground">
              Create a new SAR investigation case.
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Customer Profile */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Customer Profile</CardTitle>
              <CardDescription>
                Enter the subject&apos;s identification details.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="customer_name">Customer Name *</Label>
                <Input
                  id="customer_name"
                  value={form.customer_name}
                  onChange={(e) => updateField("customer_name", e.target.value)}
                  placeholder="Full legal name"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="customer_id">Customer ID</Label>
                <Input
                  id="customer_id"
                  value={form.customer_id}
                  onChange={(e) => updateField("customer_id", e.target.value)}
                  placeholder="Internal customer ID"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label>Customer Type</Label>
                <Select
                  value={form.customer_type}
                  onValueChange={(v) => updateField("customer_type", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="individual">Individual</SelectItem>
                    <SelectItem value="corporate">Corporate</SelectItem>
                    <SelectItem value="trust">Trust</SelectItem>
                    <SelectItem value="joint">Joint</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="occupation">Occupation</Label>
                <Input
                  id="occupation"
                  value={form.occupation}
                  onChange={(e) => updateField("occupation", e.target.value)}
                  placeholder="Stated occupation"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="jurisdiction">Jurisdiction</Label>
                <Input
                  id="jurisdiction"
                  value={form.jurisdiction}
                  onChange={(e) => updateField("jurisdiction", e.target.value)}
                  placeholder="e.g., US, IN, UK"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label>KYC Status</Label>
                <Select
                  value={form.kyc_status}
                  onValueChange={(v) => updateField("kyc_status", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="verified">Verified</SelectItem>
                    <SelectItem value="pending">Pending</SelectItem>
                    <SelectItem value="expired">Expired</SelectItem>
                    <SelectItem value="failed">Failed</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="account_type">Account Type</Label>
                <Input
                  id="account_type"
                  value={form.account_type}
                  onChange={(e) => updateField("account_type", e.target.value)}
                  placeholder="e.g., Savings, Current, Corporate"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2 flex items-end gap-2">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="pep_status"
                    checked={form.pep_status}
                    onChange={(e) => updateField("pep_status", e.target.checked)}
                    className="h-4 w-4 rounded border-input"
                    disabled={loading}
                  />
                  <Label htmlFor="pep_status">Politically Exposed Person (PEP)</Label>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Alert Information */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Alert Information</CardTitle>
              <CardDescription>
                Details about the suspicious activity alert.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="alert_typology">Alert Typology</Label>
                <Input
                  id="alert_typology"
                  value={form.alert_typology}
                  onChange={(e) => updateField("alert_typology", e.target.value)}
                  placeholder="e.g., Structuring, Layering, Smurfing"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="alert_triggered_date">Alert Triggered Date</Label>
                <Input
                  id="alert_triggered_date"
                  type="date"
                  value={form.alert_triggered_date}
                  onChange={(e) =>
                    updateField("alert_triggered_date", e.target.value)
                  }
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="overall_risk_score">
                  Overall Risk Score (0–100)
                </Label>
                <Input
                  id="overall_risk_score"
                  type="number"
                  min={0}
                  max={100}
                  value={form.overall_risk_score}
                  onChange={(e) =>
                    updateField("overall_risk_score", e.target.value)
                  }
                  placeholder="0-100"
                  disabled={loading}
                />
              </div>
            </CardContent>
          </Card>

          {/* Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Case Summary</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="case_narrative_summary">
                  Initial Narrative Summary
                </Label>
                <Textarea
                  id="case_narrative_summary"
                  value={form.case_narrative_summary}
                  onChange={(e) =>
                    updateField("case_narrative_summary", e.target.value)
                  }
                  placeholder="Brief summary of the suspicious activity…"
                  rows={4}
                  disabled={loading}
                />
              </div>
            </CardContent>
          </Card>

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Link href="/cases">
              <Button variant="outline" type="button" disabled={loading}>
                Cancel
              </Button>
            </Link>
            <Button type="submit" disabled={loading} className="gap-2">
              {loading ? (
                <>
                  <Spinner size="sm" className="text-primary-foreground" />
                  Creating…
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  Create Case
                </>
              )}
            </Button>
          </div>
        </form>
      </main>
    </>
  );
}
