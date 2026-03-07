/**
 * New Case page — /cases/new
 * Form to create a new SAR case with customer and alert details.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    customer_name: "",
    customer_id: "",
    customer_type: "individual",
    account_type: "",
    kyc_country: "",
    kyc_occupation: "",
    kyc_id_type: "passport",
    kyc_id_number: "",
    account_number: "",
    alert_id: "",
    alert_type: "",
    alert_date: "",
    alert_score: "",
    composite_risk_score: "",
    notes: "",
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
        composite_risk_score: form.composite_risk_score
          ? Number(form.composite_risk_score)
          : null,
        alert_score: form.alert_score ? Number(form.alert_score) : null,
        alert_date: form.alert_date || null,
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
                <Label htmlFor="customer_id">Customer ID *</Label>
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
                <Label htmlFor="kyc_occupation">Occupation</Label>
                <Input
                  id="kyc_occupation"
                  value={form.kyc_occupation}
                  onChange={(e) => updateField("kyc_occupation", e.target.value)}
                  placeholder="Stated occupation"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="kyc_country">KYC Country</Label>
                <Input
                  id="kyc_country"
                  value={form.kyc_country}
                  onChange={(e) => updateField("kyc_country", e.target.value)}
                  placeholder="e.g., US, IN, UK"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label>KYC ID Type</Label>
                <Select
                  value={form.kyc_id_type}
                  onValueChange={(v) => updateField("kyc_id_type", v)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="passport">Passport</SelectItem>
                    <SelectItem value="drivers_license">Drivers License</SelectItem>
                    <SelectItem value="national_id">National ID</SelectItem>
                    <SelectItem value="corporate_reg">Corporate Registration</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="kyc_id_number">KYC ID Number</Label>
                <Input
                  id="kyc_id_number"
                  value={form.kyc_id_number}
                  onChange={(e) => updateField("kyc_id_number", e.target.value)}
                  placeholder="ID document number"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="account_number">Account Number</Label>
                <Input
                  id="account_number"
                  value={form.account_number}
                  onChange={(e) => updateField("account_number", e.target.value)}
                  placeholder="Bank account number"
                  disabled={loading}
                />
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
                <Label htmlFor="alert_id">Alert ID</Label>
                <Input
                  id="alert_id"
                  value={form.alert_id}
                  onChange={(e) => updateField("alert_id", e.target.value)}
                  placeholder="Alert reference ID"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="alert_type">Alert Type</Label>
                <Input
                  id="alert_type"
                  value={form.alert_type}
                  onChange={(e) => updateField("alert_type", e.target.value)}
                  placeholder="e.g., Structuring, Layering, Smurfing"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="alert_date">Alert Date</Label>
                <Input
                  id="alert_date"
                  type="date"
                  value={form.alert_date}
                  onChange={(e) => updateField("alert_date", e.target.value)}
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="alert_score">Alert Score (0–100)</Label>
                <Input
                  id="alert_score"
                  type="number"
                  min={0}
                  max={100}
                  value={form.alert_score}
                  onChange={(e) => updateField("alert_score", e.target.value)}
                  placeholder="0-100"
                  disabled={loading}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="composite_risk_score">
                  Composite Risk Score (0–100)
                </Label>
                <Input
                  id="composite_risk_score"
                  type="number"
                  min={0}
                  max={100}
                  value={form.composite_risk_score}
                  onChange={(e) =>
                    updateField("composite_risk_score", e.target.value)
                  }
                  placeholder="0-100"
                  disabled={loading}
                />
              </div>
            </CardContent>
          </Card>

          {/* Notes */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Case Notes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <Label htmlFor="notes">Notes</Label>
                <Textarea
                  id="notes"
                  value={form.notes}
                  onChange={(e) => updateField("notes", e.target.value)}
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
