/**
 * Cases list page — /cases
 * Tabular list of all cases with pagination, status filter, and links.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
  Card,
  CardContent,
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDate, statusBadge, severityColor } from "@/lib/utils";
import { Plus, Search, ChevronLeft, ChevronRight } from "lucide-react";
import type { Case } from "@/types";

const STATUS_OPTIONS = [
  { value: "all", label: "All Statuses" },
  { value: "open", label: "Open" },
  { value: "under_review", label: "Under Review" },
  { value: "sar_generated", label: "SAR Generated" },
  { value: "escalated", label: "Escalated" },
  { value: "closed", label: "Closed" },
];

const PAGE_SIZE = 20;

export default function CasesPage() {
  const router = useRouter();

  const [cases, setCases] = useState<Case[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCases();
  }, [page, statusFilter]);

  const fetchCases = async () => {
    setLoading(true);
    try {
      const params: Record<string, any> = {
        skip: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      };
      if (statusFilter !== "all") params.status = statusFilter;

      const res = await api.get("/cases/", { params });
      const data = res.data;
      setCases(data.cases || data);
      setTotal(data.total ?? (data.cases || data).length);
    } catch (err) {
      console.error("Failed to fetch cases", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredCases = search
    ? cases.filter(
        (c) =>
          c.customer_name?.toLowerCase().includes(search.toLowerCase()) ||
          c.id.includes(search) ||
          c.alert_typology?.toLowerCase().includes(search.toLowerCase())
      )
    : cases;

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const getSeverityLabel = (score: number | null | undefined) => {
    if (score == null) return "N/A";
    if (score >= 75) return "Critical";
    if (score >= 50) return "High";
    if (score >= 25) return "Medium";
    return "Low";
  };

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 md:px-6 py-8 space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Cases</h1>
            <p className="text-muted-foreground mt-1">
              Manage and monitor all SAR cases.
            </p>
          </div>
          <Link href="/cases/new">
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New Case
            </Button>
          </Link>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4 flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, case ID, or typology…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v); setPage(0); }}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="Filter by status" />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* Table */}
        <Card>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Spinner size="lg" />
              </div>
            ) : filteredCases.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground">
                No cases found.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Customer</TableHead>
                    <TableHead className="hidden md:table-cell">Typology</TableHead>
                    <TableHead>Risk</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden lg:table-cell">Created</TableHead>
                    <TableHead className="text-right">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredCases.map((c) => {
                    const sevLabel = getSeverityLabel(c.overall_risk_score);
                    return (
                      <TableRow key={c.id}>
                        <TableCell className="font-medium">
                          {c.customer_name || `Case ${c.id.slice(0, 8)}`}
                        </TableCell>
                        <TableCell className="hidden md:table-cell text-muted-foreground">
                          {c.alert_typology || "—"}
                        </TableCell>
                        <TableCell>
                          <span
                            className={`text-xs font-semibold px-2 py-0.5 rounded-full ${severityColor(
                              sevLabel.toLowerCase() as any
                            )}`}
                          >
                            {c.overall_risk_score ?? "—"}
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={statusBadge(c.status) as any}
                            className="capitalize"
                          >
                            {c.status.replace("_", " ")}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden lg:table-cell text-muted-foreground">
                          {formatDate(c.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Link href={`/cases/${c.id}`}>
                            <Button variant="ghost" size="sm">
                              View
                            </Button>
                          </Link>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Page {page + 1} of {totalPages} ({total} cases)
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </main>
    </>
  );
}
