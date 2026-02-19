/**
 * Utility function for merging Tailwind CSS class names.
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date string or Date object to a readable format.
 */
export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format currency amounts.
 */
export function formatCurrency(amount: number, currency: string = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
  }).format(amount);
}

/**
 * Map severity to color classes.
 */
export function severityColor(severity: string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "bg-red-100 text-red-800 border-red-200";
    case "HIGH":
      return "bg-orange-100 text-orange-800 border-orange-200";
    case "MEDIUM":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "LOW":
      return "bg-green-100 text-green-800 border-green-200";
    default:
      return "bg-gray-100 text-gray-800 border-gray-200";
  }
}

/**
 * Map confidence level to color classes.
 */
export function confidenceColor(level: string): string {
  switch (level) {
    case "HIGH":
      return "text-green-700 bg-green-50";
    case "MEDIUM":
      return "text-yellow-700 bg-yellow-50";
    case "LOW":
      return "text-red-700 bg-red-50";
    default:
      return "text-gray-700 bg-gray-50";
  }
}

/**
 * Map case status to display label and color.
 */
export function statusBadge(status: string): { label: string; color: string } {
  const map: Record<string, { label: string; color: string }> = {
    open: { label: "Open", color: "bg-blue-100 text-blue-800" },
    under_review: { label: "Under Review", color: "bg-yellow-100 text-yellow-800" },
    sar_generated: { label: "SAR Generated", color: "bg-purple-100 text-purple-800" },
    escalated: { label: "Escalated", color: "bg-red-100 text-red-800" },
    closed: { label: "Closed", color: "bg-gray-100 text-gray-800" },
  };
  return map[status] || { label: status, color: "bg-gray-100 text-gray-800" };
}
