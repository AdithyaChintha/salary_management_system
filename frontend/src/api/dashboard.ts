import { request } from "./client";

export type DashboardFilters = {
  country: string;
  department: string;
  min_salary_usd: string;
  max_salary_usd: string;
};

export type Distribution = { name: string; headcount: number };
export type PayBand = {
  label: string;
  lower_usd: string | null;
  upper_usd: string | null;
  headcount: number;
};

export type DashboardResponse = {
  summary: {
    headcount: number;
    total_payroll_usd: string;
    average_salary_usd: string | null;
    median_salary_usd: string | null;
  };
  by_country: Distribution[];
  by_department: Distribution[];
  pay_bands: PayBand[];
  quartile_cutoffs_usd: [string | null, string | null, string | null];
  highest_salary_usd: string | null;
  lowest_salary_usd: string | null;
};

export function getDashboard(filters: DashboardFilters, signal?: AbortSignal) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value.trim()) params.set(key, value.trim());
  }
  const query = params.toString();
  return request<DashboardResponse>(`/analytics/dashboard${query ? `?${query}` : ""}`, { signal });
}
