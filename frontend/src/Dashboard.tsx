import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getDashboard,
  type DashboardFilters,
  type DashboardResponse,
  type Distribution,
} from "./api/dashboard";
import { COUNTRIES, DEPARTMENTS, usd } from "./employee-data";

const EMPTY_FILTERS: DashboardFilters = {
  country: "",
  department: "",
  min_salary_usd: "",
  max_salary_usd: "",
};

const NUMBER = new Intl.NumberFormat("en-US");
const BAND_NAMES: Record<string, string> = {
  p0_p25: "Bottom 25%",
  p25_p50: "25–50%",
  p50_p75: "50–75%",
  p75_p100: "Top 25%",
};

function money(value: string | null): string {
  return value === null ? "—" : usd(value);
}

function compactMoney(value: string | null): string {
  if (value === null) return "—";
  const amount = Number(value);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(amount);
}

function DistributionChart({
  title,
  subtitle,
  data,
  color,
}: {
  title: string;
  subtitle: string;
  data: Distribution[];
  color: string;
}) {
  return (
    <section className="analytics-panel" aria-label={title}>
      <div className="analytics-panel-heading">
        <div>
          <h2>{title}</h2>
          <p>{subtitle}</p>
        </div>
        <span className="chart-unit">HEADCOUNT</span>
      </div>
      {data.length ? (
        <>
          <div
            className="distribution-chart"
            style={{ height: Math.max(230, data.length * 38 + 35) }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 6, right: 35, left: 5, bottom: 4 }}
              >
                <CartesianGrid stroke="#ecf0f3" horizontal={false} />
                <XAxis
                  type="number"
                  allowDecimals={false}
                  tick={{ fill: "#8a98a8", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={112}
                  tick={{ fill: "#54677b", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "#f5f8fa" }}
                  formatter={(value: number) => [NUMBER.format(value), "Employees"]}
                />
                <Bar dataKey="headcount" fill={color} radius={[0, 5, 5, 0]} barSize={15} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <ul className="chart-summary-list" aria-label={`${title} values`}>
            {data.map((item) => (
              <li key={item.name}>
                <span>{item.name}</span>
                <strong>{NUMBER.format(item.headcount)}</strong>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <p className="chart-empty">No matching employees for this breakdown.</p>
      )}
    </section>
  );
}

export function Dashboard() {
  const [filters, setFilters] = useState<DashboardFilters>(EMPTY_FILTERS);
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setData(null);
    setError("");

    const minimum = filters.min_salary_usd ? Number(filters.min_salary_usd) : null;
    const maximum = filters.max_salary_usd ? Number(filters.max_salary_usd) : null;
    if ((minimum !== null && minimum < 0) || (maximum !== null && maximum < 0)) {
      setError("Salary limits must be zero or greater.");
      setLoading(false);
      return () => controller.abort();
    }
    if (minimum !== null && maximum !== null && minimum > maximum) {
      setError("Minimum salary cannot exceed maximum salary.");
      setLoading(false);
      return () => controller.abort();
    }

    const timer = window.setTimeout(() => {
      getDashboard(filters, controller.signal)
        .then(setData)
        .catch((cause) => {
          if (!controller.signal.aborted) {
            setError(cause instanceof Error ? cause.message : "Could not load the dashboard.");
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [filters, revision]);

  function change(key: keyof DashboardFilters, value: string) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  const bands =
    data?.pay_bands.map((band, index) => ({
      name: `Q${index + 1}`,
      label: BAND_NAMES[band.label] ?? band.label,
      headcount: band.headcount,
      range: `${compactMoney(band.lower_usd)} – ${compactMoney(band.upper_usd)}`,
    })) ?? [];
  const hasFilters = Object.values(filters).some(Boolean);

  return (
    <div className="dashboard-page">
      <div className="page-heading dashboard-heading">
        <div>
          <span className="eyebrow">WORKFORCE INTELLIGENCE</span>
          <h1>Analytics overview</h1>
          <p>A clear view of your current active workforce and pay distribution.</p>
        </div>
        <span className="live-badge">
          <span className="status-dot" /> Active employees only
        </span>
      </div>

      <section className="dashboard-filterbar" aria-label="Dashboard filters">
        <div className="filterbar-title">
          <span className="filter-symbol" aria-hidden="true">
            ≡
          </span>
          <strong>Filters</strong>
          <small>Applies to every metric below</small>
        </div>
        <div className="dashboard-filter-grid">
          <label>
            Country
            <select
              aria-label="Dashboard country"
              value={filters.country}
              onChange={(event) => change("country", event.target.value)}
            >
              <option value="">All countries</option>
              {COUNTRIES.map((country) => (
                <option key={country.code} value={country.code}>
                  {country.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Department
            <select
              aria-label="Dashboard department"
              value={filters.department}
              onChange={(event) => change("department", event.target.value)}
            >
              <option value="">All departments</option>
              {DEPARTMENTS.map((department) => (
                <option key={department} value={department}>
                  {department}
                </option>
              ))}
            </select>
          </label>
          <label>
            Min salary (USD)
            <input
              aria-label="Minimum salary USD"
              type="number"
              min="0"
              step="0.01"
              placeholder="No minimum"
              value={filters.min_salary_usd}
              onChange={(event) => change("min_salary_usd", event.target.value)}
            />
          </label>
          <label>
            Max salary (USD)
            <input
              aria-label="Maximum salary USD"
              type="number"
              min="0"
              step="0.01"
              placeholder="No maximum"
              value={filters.max_salary_usd}
              onChange={(event) => change("max_salary_usd", event.target.value)}
            />
          </label>
        </div>
        {hasFilters && (
          <button
            className="clear-button dashboard-clear"
            onClick={() => setFilters(EMPTY_FILTERS)}
          >
            Clear all filters
          </button>
        )}
      </section>

      {loading && (
        <div className="dashboard-message" role="status">
          <span className="spinner" /> Updating dashboard…
        </div>
      )}
      {!loading && error && (
        <div className="dashboard-message dashboard-error" role="alert">
          <strong>Dashboard unavailable</strong>
          <span>{error}</span>
          <button
            className="button button-quiet"
            onClick={() => setRevision((current) => current + 1)}
          >
            Retry
          </button>
        </div>
      )}
      {!loading && data && (
        <>
          {data.summary.headcount === 0 && (
            <div className="dashboard-empty" role="status">
              No active employees match these filters. Adjust the selection to see workforce
              metrics.
            </div>
          )}
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-symbol mint">◎</span>
              <span className="kpi-label">ACTIVE HEADCOUNT</span>
              <strong>{NUMBER.format(data.summary.headcount)}</strong>
              <small>Employees in selection</small>
            </div>
            <div className="kpi-card">
              <span className="kpi-symbol blue">$</span>
              <span className="kpi-label">TOTAL PAYROLL</span>
              <strong>{money(data.summary.total_payroll_usd)}</strong>
              <small>Annual · normalized USD</small>
            </div>
            <div className="kpi-card">
              <span className="kpi-symbol purple">≈</span>
              <span className="kpi-label">AVERAGE SALARY</span>
              <strong>{money(data.summary.average_salary_usd)}</strong>
              <small>Annual · per employee</small>
            </div>
            <div className="kpi-card">
              <span className="kpi-symbol peach">◈</span>
              <span className="kpi-label">MEDIAN SALARY</span>
              <strong>{money(data.summary.median_salary_usd)}</strong>
              <small>50th percentile</small>
            </div>
          </div>

          <div className="analytics-grid">
            <DistributionChart
              title="By department"
              subtitle="Where the workforce is concentrated"
              data={data.by_department}
              color="#148679"
            />
            <DistributionChart
              title="By country"
              subtitle="Employees across supported locations"
              data={data.by_country}
              color="#507fa7"
            />
          </div>

          <div className="analytics-grid bottom-grid">
            <section className="analytics-panel pay-panel" aria-label="Percentile pay bands">
              <div className="analytics-panel-heading">
                <div>
                  <h2>Percentile pay bands</h2>
                  <p>Headcount in each quartile of the filtered workforce</p>
                </div>
                <span className="chart-unit">SALARY · USD</span>
              </div>
              {data.summary.headcount ? (
                <>
                  <div className="pay-chart">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={bands} margin={{ top: 8, right: 10, left: -20, bottom: 2 }}>
                        <CartesianGrid stroke="#ecf0f3" vertical={false} />
                        <XAxis
                          dataKey="name"
                          tick={{ fill: "#68798a", fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <YAxis
                          allowDecimals={false}
                          tick={{ fill: "#8a98a8", fontSize: 11 }}
                          axisLine={false}
                          tickLine={false}
                        />
                        <Tooltip
                          formatter={(value: number) => [NUMBER.format(value), "Employees"]}
                        />
                        <Bar dataKey="headcount" radius={[6, 6, 0, 0]} barSize={43}>
                          {bands.map((band, index) => (
                            <Cell
                              key={band.name}
                              fill={["#a5c8c2", "#65afa5", "#2e9789", "#126f66"][index]}
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <ul className="band-list" aria-label="Pay band values">
                    {bands.map((band) => (
                      <li key={band.name}>
                        <strong>{band.label}</strong>
                        <span>{band.range}</span>
                        <b>{NUMBER.format(band.headcount)}</b>
                      </li>
                    ))}
                  </ul>
                  <p className="chart-note">
                    Quartile cutoffs are recalculated from the current filtered selection.
                  </p>
                </>
              ) : (
                <p className="chart-empty">No pay bands for an empty selection.</p>
              )}
            </section>
            <section className="analytics-panel extremes-panel" aria-label="Salary extremes">
              <div className="analytics-panel-heading">
                <div>
                  <h2>Salary range</h2>
                  <p>Annual normalized salary in the selection</p>
                </div>
              </div>
              <div className="extreme-box high">
                <span>HIGHEST SALARY</span>
                <strong>{money(data.highest_salary_usd)}</strong>
                <small>Top of current selection</small>
              </div>
              <div className="extreme-box low">
                <span>LOWEST SALARY</span>
                <strong>{money(data.lowest_salary_usd)}</strong>
                <small>Bottom of current selection</small>
              </div>
              <p className="chart-note">
                Includes active employees only. All amounts are shown in USD.
              </p>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
