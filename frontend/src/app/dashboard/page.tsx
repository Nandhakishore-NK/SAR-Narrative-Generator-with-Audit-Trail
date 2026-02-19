/**
 * Dashboard page — /dashboard
 * Shows case summary cards, recent alerts, risk overview.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { api } from "@/lib/api";
import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import {
  severityColor,
  statusBadge,
  formatDate,
  formatCurrency,
} from "@/lib/utils";
import {
  AlertTriangle,
  FileText,
  ShieldAlert,
  CheckCircle2,
  FolderOpen,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import type { Case } from "@/types";

interface DashboardStats {
  total: number;
  open: number;
  underReview: number;
  sarGenerated: number;
  escalated: number;
  closed: number;
}

export default function DashboardPage() {
  const { user, token } = useAuth();
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      router.push("/login");
      return;
    }
    fetchDashboardData();
  }, [token]);

  const fetchDashboardData = async () => {
    try {
      const res = await api.get("/cases/?limit=100");
      const allCases: Case[] = res.data.cases || res.data;
      setCases(allCases);

      const s: DashboardStats = {
        total: allCases.length,
        open: allCases.filter((c) => c.status === "open").length,
        underReview: allCases.filter((c) => c.status === "under_review").length,
        sarGenerated: allCases.filter((c) => c.status === "sar_generated").length,
        escalated: allCases.filter((c) => c.status === "escalated").length,
        closed: allCases.filter((c) => c.status === "closed").length,
      };
      setStats(s);
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
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

  const recentCases = [...cases]
    .sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    )
    .slice(0, 5);

  const highRiskCases = cases
    .filter((c) => c.overall_risk_score && c.overall_risk_score >= 75)
    .slice(0, 5);

  const statCards = [
    {
      label: "Total Cases",
      value: stats?.total ?? 0,
      icon: FolderOpen,
      color: "text-slate-600",
      bg: "bg-slate-100",
    },
    {
      label: "Open",
      value: stats?.open ?? 0,
      icon: AlertTriangle,
      color: "text-amber-600",
      bg: "bg-amber-50",
    },
    {
      label: "Under Review",
      value: stats?.underReview ?? 0,
      icon: FileText,
      color: "text-blue-600",
      bg: "bg-blue-50",
    },
    {
      label: "SAR Generated",
      value: stats?.sarGenerated ?? 0,
      icon: ShieldAlert,
      color: "text-purple-600",
      bg: "bg-purple-50",
    },
    {
      label: "Escalated",
      value: stats?.escalated ?? 0,
      icon: TrendingUp,
      color: "text-red-600",
      bg: "bg-red-50",
    },
    {
      label: "Closed",
      value: stats?.closed ?? 0,
      icon: CheckCircle2,
      color: "text-emerald-600",
      bg: "bg-emerald-50",
    },
  ];

  return (
    <>
      <Navbar />
      <main className="container mx-auto px-4 md:px-6 py-8 space-y-8">
        {/* Welcome */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Welcome back, {user.name}. Here&apos;s your compliance overview.
          </p>
        </div>

        {/* Stat Cards */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {statCards.map((sc) => {
            const Icon = sc.icon;
            return (
              <Card key={sc.label}>
                <CardContent className="p-4 flex flex-col items-center text-center gap-2">
                  <div
                    className={`flex items-center justify-center h-10 w-10 rounded-xl ${sc.bg}`}
                  >
                    <Icon className={`h-5 w-5 ${sc.color}`} />
                  </div>
                  <p className="text-2xl font-bold">{sc.value}</p>
                  <p className="text-xs text-muted-foreground">{sc.label}</p>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Recent Cases */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <div>
                <CardTitle className="text-lg">Recent Cases</CardTitle>
                <CardDescription>Latest activity</CardDescription>
              </div>
              <Link href="/cases">
                <Button variant="ghost" size="sm" className="gap-1">
                  View All <ArrowRight className="h-3 w-3" />
                </Button>
              </Link>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentCases.length === 0 ? (
                <p className="text-sm text-muted-foreground">No cases yet.</p>
              ) : (
                recentCases.map((c) => (
                  <Link
                    key={c.id}
                    href={`/cases/${c.id}`}
                    className="flex items-center justify-between rounded-lg p-3 hover:bg-muted/50 transition-colors border"
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {c.customer_name || `Case ${c.id.slice(0, 8)}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDate(c.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {c.overall_risk_score != null && (
                        <span
                          className={`text-xs font-semibold ${severityColor(
                            c.overall_risk_score >= 75
                              ? "critical"
                              : c.overall_risk_score >= 50
                              ? "high"
                              : c.overall_risk_score >= 25
                              ? "medium"
                              : "low"
                          )}`}
                        >
                          Risk: {c.overall_risk_score}
                        </span>
                      )}
                      <Badge variant={statusBadge(c.status) as any}>
                        {c.status.replace("_", " ")}
                      </Badge>
                    </div>
                  </Link>
                ))
              )}
            </CardContent>
          </Card>

          {/* High Risk Cases */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg">High Risk Alerts</CardTitle>
              <CardDescription>
                Cases with risk score &ge; 75
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {highRiskCases.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No high-risk cases detected.
                </p>
              ) : (
                highRiskCases.map((c) => (
                  <Link
                    key={c.id}
                    href={`/cases/${c.id}`}
                    className="flex items-center justify-between rounded-lg p-3 hover:bg-muted/50 transition-colors border border-red-200"
                  >
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {c.customer_name || `Case ${c.id.slice(0, 8)}`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {c.alert_typology || "Unknown typology"}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="destructive">
                        Risk: {c.overall_risk_score}
                      </Badge>
                    </div>
                  </Link>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </main>
    </>
  );
}
