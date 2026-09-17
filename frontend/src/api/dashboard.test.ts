import { afterEach, expect, it, vi } from "vitest";

import { getDashboard } from "./dashboard";

afterEach(() => vi.unstubAllGlobals());

it("sends every selected filter to the dashboard endpoint in one request", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ summary: { headcount: 2 } }),
  });
  vi.stubGlobal("fetch", fetchMock);

  await getDashboard({
    country: "IN",
    department: "Engineering",
    min_salary_usd: "40000",
    max_salary_usd: "90000",
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [url] = fetchMock.mock.calls[0];
  expect(url).toContain("/api/v1/analytics/dashboard?");
  const params = new URL(url).searchParams;
  expect(Object.fromEntries(params)).toEqual({
    country: "IN",
    department: "Engineering",
    min_salary_usd: "40000",
    max_salary_usd: "90000",
  });
});
