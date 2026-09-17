import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { App } from "./App";
import { getDashboard, type DashboardResponse } from "./api/dashboard";

vi.mock("./api/dashboard", () => ({ getDashboard: vi.fn() }));

const overview: DashboardResponse = {
  summary: {
    headcount: 8,
    total_payroll_usd: "360000.00",
    average_salary_usd: "45000.00",
    median_salary_usd: "45000.00",
  },
  by_country: [
    { name: "India", headcount: 4 },
    { name: "United States", headcount: 4 },
  ],
  by_department: [
    { name: "Engineering", headcount: 5 },
    { name: "Finance", headcount: 3 },
  ],
  pay_bands: [
    { label: "p0_p25", lower_usd: "10000.00", upper_usd: "27500.00", headcount: 2 },
    { label: "p25_p50", lower_usd: "27500.00", upper_usd: "45000.00", headcount: 2 },
    { label: "p50_p75", lower_usd: "45000.00", upper_usd: "62500.00", headcount: 2 },
    { label: "p75_p100", lower_usd: "62500.00", upper_usd: "80000.00", headcount: 2 },
  ],
  quartile_cutoffs_usd: ["27500.00", "45000.00", "62500.00"],
  highest_salary_usd: "80000.00",
  lowest_salary_usd: "10000.00",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
    width: 800,
    height: 400,
    x: 0,
    y: 0,
    top: 0,
    right: 800,
    bottom: 400,
    left: 0,
    toJSON: () => ({}),
  });
  vi.mocked(getDashboard).mockResolvedValue(overview);
});

afterEach(() => vi.restoreAllMocks());

it("shows all KPIs, breakdowns, pay bands, and salary extrema", async () => {
  render(<App />);
  expect(await screen.findByText("Analytics overview")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByText("$360,000")).toBeInTheDocument());
  expect(screen.getByText("ACTIVE HEADCOUNT")).toBeInTheDocument();
  expect(screen.getByText("AVERAGE SALARY")).toBeInTheDocument();
  expect(screen.getByText("MEDIAN SALARY")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "By country" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "By department" })).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Percentile pay bands" })).toBeInTheDocument();
  expect(screen.getByText("$80,000")).toBeInTheDocument();
  expect(screen.getByText("$10,000")).toBeInTheDocument();
  expect(getDashboard).toHaveBeenCalledWith(
    { country: "", department: "", min_salary_usd: "", max_salary_usd: "" },
    expect.any(AbortSignal),
  );
});

it("applies one filter set to every dashboard component", async () => {
  const user = userEvent.setup();
  const filtered: DashboardResponse = {
    ...overview,
    summary: {
      headcount: 2,
      total_payroll_usd: "50000.00",
      average_salary_usd: "25000.00",
      median_salary_usd: "25000.00",
    },
    by_country: [{ name: "India", headcount: 2 }],
    by_department: [{ name: "Engineering", headcount: 2 }],
    pay_bands: overview.pay_bands.map((band, index) => ({ ...band, headcount: index < 2 ? 1 : 0 })),
    highest_salary_usd: "30000.00",
    lowest_salary_usd: "20000.00",
  };
  vi.mocked(getDashboard).mockImplementation(async (filters) =>
    filters.country === "IN" ? filtered : overview,
  );
  render(<App />);
  await screen.findByText("$360,000");
  await user.selectOptions(screen.getByLabelText("Dashboard country"), "IN");
  await user.selectOptions(screen.getByLabelText("Dashboard department"), "Engineering");
  fireEvent.change(screen.getByLabelText("Minimum salary USD"), { target: { value: "20000" } });
  fireEvent.change(screen.getByLabelText("Maximum salary USD"), { target: { value: "30000" } });
  await waitFor(() =>
    expect(getDashboard).toHaveBeenLastCalledWith(
      {
        country: "IN",
        department: "Engineering",
        min_salary_usd: "20000",
        max_salary_usd: "30000",
      },
      expect.any(AbortSignal),
    ),
  );
  expect(await screen.findByText("$50,000")).toBeInTheDocument();
  expect(screen.getByText("$30,000")).toBeInTheDocument();
  expect(screen.getByText("$20,000")).toBeInTheDocument();
  expect(screen.queryByText("$360,000")).not.toBeInTheDocument();
});

it("validates salary range before requesting data and can clear filters", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("$360,000");
  const previousCalls = vi.mocked(getDashboard).mock.calls.length;
  fireEvent.change(screen.getByLabelText("Minimum salary USD"), { target: { value: "90000" } });
  fireEvent.change(screen.getByLabelText("Maximum salary USD"), { target: { value: "40000" } });
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Minimum salary cannot exceed maximum salary",
  );
  expect(vi.mocked(getDashboard).mock.calls).toHaveLength(previousCalls);
  await user.click(screen.getByRole("button", { name: "Clear all filters" }));
  await waitFor(() => expect(getDashboard).toHaveBeenCalledTimes(previousCalls + 1));
});

it("shows an empty workforce state and an API error state", async () => {
  vi.mocked(getDashboard).mockResolvedValueOnce({
    ...overview,
    summary: {
      headcount: 0,
      total_payroll_usd: "0.00",
      average_salary_usd: null,
      median_salary_usd: null,
    },
    by_country: [],
    by_department: [],
    pay_bands: [],
    highest_salary_usd: null,
    lowest_salary_usd: null,
  });
  const view = render(<App />);
  expect(await screen.findByText(/No active employees match/)).toBeInTheDocument();
  view.unmount();
  vi.mocked(getDashboard).mockRejectedValueOnce(new Error("Dashboard API unavailable"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Dashboard API unavailable");
});
