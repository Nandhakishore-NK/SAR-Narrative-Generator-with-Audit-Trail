/**
 * Override Modal component — used in case detail page.
 * Allows analyst to submit sentence-level overrides with reason codes.
 */

"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AlertCircle } from "lucide-react";
import type { NarrativeSentence } from "@/types";

const REASON_CODES = [
  { value: "factual_correction", label: "Factual Correction" },
  { value: "regulatory_alignment", label: "Regulatory Alignment" },
  { value: "additional_context", label: "Additional Context" },
  { value: "risk_reassessment", label: "Risk Reassessment" },
  { value: "typographical_error", label: "Typographical Error" },
  { value: "legal_counsel_advice", label: "Legal Counsel Advice" },
  { value: "new_evidence", label: "New Evidence" },
];

interface OverrideModalProps {
  sentence: NarrativeSentence | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function OverrideModal({
  sentence,
  open,
  onOpenChange,
  onSuccess,
}: OverrideModalProps) {
  const [modifiedText, setModifiedText] = useState("");
  const [reasonCode, setReasonCode] = useState("");
  const [justification, setJustification] = useState("");
  const [evidenceRef, setEvidenceRef] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOpen = (isOpen: boolean) => {
    if (isOpen && sentence) {
      setModifiedText(sentence.sentence_text);
      setReasonCode("");
      setJustification("");
      setEvidenceRef("");
      setError(null);
    }
    onOpenChange(isOpen);
  };

  const handleSubmit = async () => {
    setError(null);
    if (!reasonCode) {
      setError("Override reason code is required.");
      return;
    }
    if (!justification.trim()) {
      setError("Justification is required for compliance audit trail.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/overrides/", {
        sentence_id: sentence?.id,
        modified_text: modifiedText,
        override_reason_code: reasonCode,
        justification: justification.trim(),
        evidence_reference: evidenceRef.trim() || null,
      });
      onSuccess();
      onOpenChange(false);
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        "Failed to submit override. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  if (!sentence) return null;

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Override Narrative Sentence</DialogTitle>
          <DialogDescription>
            All overrides require a reason code, justification, and supervisor
            approval. Changes are recorded in the immutable audit trail.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Original text (read-only) */}
          <div className="space-y-2">
            <Label className="text-muted-foreground text-xs uppercase tracking-wide">
              Original Sentence
            </Label>
            <div className="rounded-lg bg-muted p-3 text-sm font-mono">
              {sentence.sentence_text}
            </div>
            <p className="text-xs text-muted-foreground">
              Hash: <code className="text-[10px]">{sentence.sentence_hash}</code>
            </p>
          </div>

          {/* Modified text */}
          <div className="space-y-2">
            <Label htmlFor="modified-text">Modified Sentence</Label>
            <Textarea
              id="modified-text"
              value={modifiedText}
              onChange={(e) => setModifiedText(e.target.value)}
              rows={4}
              disabled={loading}
            />
          </div>

          {/* Reason Code */}
          <div className="space-y-2">
            <Label>Reason Code *</Label>
            <Select value={reasonCode} onValueChange={setReasonCode}>
              <SelectTrigger>
                <SelectValue placeholder="Select override reason…" />
              </SelectTrigger>
              <SelectContent>
                {REASON_CODES.map((rc) => (
                  <SelectItem key={rc.value} value={rc.value}>
                    {rc.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Justification */}
          <div className="space-y-2">
            <Label htmlFor="justification">Justification *</Label>
            <Textarea
              id="justification"
              placeholder="Provide detailed justification for the override…"
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              rows={3}
              disabled={loading}
            />
          </div>

          {/* Evidence Reference */}
          <div className="space-y-2">
            <Label htmlFor="evidence-ref">Evidence Reference</Label>
            <Input
              id="evidence-ref"
              placeholder="e.g., Document ID, transaction ref, legal memo #"
              value={evidenceRef}
              onChange={(e) => setEvidenceRef(e.target.value)}
              disabled={loading}
            />
          </div>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? (
              <span className="flex items-center gap-2">
                <Spinner size="sm" className="text-primary-foreground" />
                Submitting…
              </span>
            ) : (
              "Submit Override"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
