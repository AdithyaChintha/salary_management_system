import { useEffect, useState } from "react";

import {
  listEmployees,
  setEmployeeActive,
  type Employee,
  type EmployeePage,
  type EmployeeQuery,
} from "./api/employees";
import { COUNTRIES, DEPARTMENTS, countryName, usd } from "./employee-data";
import { Dashboard } from "./Dashboard";
import { EmployeeForm, type FormMode } from "./EmployeeForm";

const INITIAL_QUERY: EmployeeQuery = {
  search: "",
  country: "",
  department: "",
  is_active: "true",
  min_salary_usd: "",
  max_salary_usd: "",
  page: 1,
  page_size: 10,
  sort_by: "name",
  sort_order: "asc",
};

export function App() {
  const [view, setView] = useState<"employees" | "dashboard">("dashboard");
  const [query, setQuery] = useState<EmployeeQuery>(INITIAL_QUERY);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState<EmployeePage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [formMode, setFormMode] = useState<FormMode | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setQuery((current) =>
        current.search === search ? current : { ...current, search, page: 1 },
      );
    }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    if (view !== "employees") return;
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setPage(null);
    listEmployees(query, controller.signal)
      .then((result) => {
        const lastAvailablePage = Math.max(1, Math.ceil(result.total / query.page_size));
        if (query.page > lastAvailablePage) {
          setQuery((current) => ({ ...current, page: lastAvailablePage }));
        } else {
          setPage(result);
        }
      })
      .catch((cause) => {
        if (!controller.signal.aborted)
          setError(cause instanceof Error ? cause.message : "Could not load employees.");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [query, revision, view]);

  const total = page?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / query.page_size));
  const first = total ? (query.page - 1) * query.page_size + 1 : 0;
  const last = Math.min(query.page * query.page_size, total);
  const hasFilters = Boolean(
    query.search ||
    query.country ||
    query.department ||
    query.min_salary_usd ||
    query.max_salary_usd ||
    query.is_active !== "true",
  );

  function filter<K extends keyof EmployeeQuery>(key: K, value: EmployeeQuery[K]) {
    setQuery((current) => ({ ...current, [key]: value, page: 1 }));
  }

  function sort(by: EmployeeQuery["sort_by"]) {
    setQuery((current) => ({
      ...current,
      sort_by: by,
      sort_order: current.sort_by === by && current.sort_order === "asc" ? "desc" : "asc",
      page: 1,
    }));
  }

  async function changeStatus(employee: Employee) {
    const action = employee.is_active ? "deactivate" : "reactivate";
    if (
      employee.is_active &&
      !window.confirm(
        `Deactivate ${employee.name}? They will remain in the database but cannot be edited until reactivated.`,
      )
    )
      return;
    setBusyId(employee.employee_id);
    setNotice("");
    setError("");
    try {
      await setEmployeeActive(employee.employee_id, !employee.is_active);
      setNotice(
        `${employee.name} ${employee.is_active ? "deactivated" : "reactivated"} successfully.`,
      );
      setRevision((value) => value + 1);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : `Could not ${action} employee.`);
    } finally {
      setBusyId(null);
    }
  }

  function saved() {
    setNotice(
      formMode?.kind === "create"
        ? "Employee added successfully."
        : "Employee updated successfully.",
    );
    setFormMode(null);
    setRevision((value) => value + 1);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">S</span>
          <span>
            <strong>Salarybase</strong>
            <small>WORKFORCE CONSOLE</small>
          </span>
        </div>
        <div className="sidebar-section">WORKSPACE</div>
        <button
          className={`nav-item ${view === "dashboard" ? "active" : ""}`}
          onClick={() => setView("dashboard")}
        >
          <span aria-hidden="true">◫</span> Analytics
        </button>
        <button
          className={`nav-item ${view === "employees" ? "active" : ""}`}
          onClick={() => setView("employees")}
        >
          <span aria-hidden="true">▦</span> Employees
        </button>
        <div className="sidebar-bottom">
          <span className="status-dot" /> Internal management workspace
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <span>
            Workspace / <strong>{view === "dashboard" ? "Analytics" : "Employees"}</strong>
          </span>
          <span>Salary Management System</span>
        </header>
        <div className="content-wrap">
          {view === "dashboard" ? (
            <Dashboard />
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <span className="eyebrow">WORKFORCE DIRECTORY</span>
                  <h1>Employees</h1>
                  <p>Manage employee records, salaries, and active status in one place.</p>
                </div>
                <button
                  className="button button-primary"
                  onClick={() => setFormMode({ kind: "create" })}
                >
                  ＋ Add employee
                </button>
              </div>
              {notice && (
                <div className="notice success" role="status">
                  {notice}
                  <button aria-label="Dismiss notification" onClick={() => setNotice("")}>
                    ×
                  </button>
                </div>
              )}
              {error && (
                <div className="notice error" role="alert">
                  {error}
                  <button aria-label="Dismiss error" onClick={() => setError("")}>
                    ×
                  </button>
                </div>
              )}

              <section className="panel" aria-label="Employee directory">
                <div className="panel-header">
                  <div>
                    <h2>Employee directory</h2>
                    <p>Search and filter your workforce records.</p>
                  </div>
                  <span className="count-pill">{loading ? "Loading…" : `${total} records`}</span>
                </div>
                <div className="filters">
                  <label className="search-field">
                    <span className="visually-hidden">Search by name or employee ID</span>
                    <span aria-hidden="true">⌕</span>
                    <input
                      aria-label="Search by name or employee ID"
                      value={search}
                      onChange={(event) => setSearch(event.target.value)}
                      placeholder="Search name or employee ID"
                    />
                  </label>
                  <label>
                    <span className="visually-hidden">Filter by country</span>
                    <select
                      value={query.country}
                      onChange={(event) => filter("country", event.target.value)}
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
                    <span className="visually-hidden">Filter by department</span>
                    <select
                      value={query.department}
                      onChange={(event) => filter("department", event.target.value)}
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
                    <span className="visually-hidden">Filter by status</span>
                    <select
                      value={query.is_active}
                      onChange={(event) => filter("is_active", event.target.value)}
                    >
                      <option value="true">Active only</option>
                      <option value="false">Inactive only</option>
                      <option value="">All statuses</option>
                    </select>
                  </label>
                </div>
                <div className="secondary-filters">
                  <span>USD salary range</span>
                  <label>
                    <span className="visually-hidden">Minimum USD salary</span>
                    <input
                      type="number"
                      min="0"
                      placeholder="Minimum"
                      value={query.min_salary_usd}
                      onChange={(event) => filter("min_salary_usd", event.target.value)}
                    />
                  </label>
                  <span>—</span>
                  <label>
                    <span className="visually-hidden">Maximum USD salary</span>
                    <input
                      type="number"
                      min="0"
                      placeholder="Maximum"
                      value={query.max_salary_usd}
                      onChange={(event) => filter("max_salary_usd", event.target.value)}
                    />
                  </label>
                  {hasFilters && (
                    <button
                      className="clear-button"
                      onClick={() => {
                        setSearch("");
                        setQuery(INITIAL_QUERY);
                      }}
                    >
                      Clear filters
                    </button>
                  )}
                </div>

                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th
                          aria-sort={
                            query.sort_by === "name"
                              ? query.sort_order === "asc"
                                ? "ascending"
                                : "descending"
                              : "none"
                          }
                        >
                          <button onClick={() => sort("name")}>
                            Employee{" "}
                            {query.sort_by === "name"
                              ? query.sort_order === "asc"
                                ? "↑"
                                : "↓"
                              : "↕"}
                          </button>
                        </th>
                        <th
                          aria-sort={
                            query.sort_by === "employee_id"
                              ? query.sort_order === "asc"
                                ? "ascending"
                                : "descending"
                              : "none"
                          }
                        >
                          <button onClick={() => sort("employee_id")}>
                            Employee ID{" "}
                            {query.sort_by === "employee_id"
                              ? query.sort_order === "asc"
                                ? "↑"
                                : "↓"
                              : "↕"}
                          </button>
                        </th>
                        <th>Country</th>
                        <th>Department</th>
                        <th>Role</th>
                        <th
                          aria-sort={
                            query.sort_by === "salary_usd"
                              ? query.sort_order === "asc"
                                ? "ascending"
                                : "descending"
                              : "none"
                          }
                        >
                          <button onClick={() => sort("salary_usd")}>
                            Salary (USD){" "}
                            {query.sort_by === "salary_usd"
                              ? query.sort_order === "asc"
                                ? "↑"
                                : "↓"
                              : "↕"}
                          </button>
                        </th>
                        <th>Status</th>
                        <th className="actions-heading">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {!loading &&
                        page?.items.map((employee) => (
                          <tr key={employee.employee_id}>
                            <td>
                              <div className="employee-cell">
                                <span className="avatar">
                                  {employee.name.slice(0, 1).toUpperCase()}
                                </span>
                                <strong>{employee.name}</strong>
                              </div>
                            </td>
                            <td className="mono">{employee.employee_id}</td>
                            <td>{countryName(employee.country)}</td>
                            <td>{employee.department}</td>
                            <td>{employee.role}</td>
                            <td className="money">{usd(employee.salary_usd)}</td>
                            <td>
                              <span
                                className={`status-badge ${employee.is_active ? "status-active" : "status-inactive"}`}
                              >
                                {employee.is_active ? "Active" : "Inactive"}
                              </span>
                            </td>
                            <td>
                              <div className="row-actions">
                                {employee.is_active && (
                                  <button onClick={() => setFormMode({ kind: "edit", employee })}>
                                    Edit
                                  </button>
                                )}
                                <button
                                  disabled={busyId === employee.employee_id}
                                  onClick={() => changeStatus(employee)}
                                >
                                  {busyId === employee.employee_id
                                    ? "Working…"
                                    : employee.is_active
                                      ? "Deactivate"
                                      : "Reactivate"}
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                  {loading && (
                    <div className="table-state" role="status">
                      <span className="spinner" />
                      Loading employees…
                    </div>
                  )}
                  {!loading && !error && page?.items.length === 0 && (
                    <div className="table-state empty-state">
                      <span className="empty-icon">⌕</span>
                      <strong>No employees found</strong>
                      <p>
                        {hasFilters
                          ? "Try adjusting your search or filters."
                          : "Add your first employee to get started."}
                      </p>
                    </div>
                  )}
                  {!loading && error && (
                    <div className="table-state empty-state">
                      <strong>Unable to load employees</strong>
                      <button
                        className="button button-quiet"
                        onClick={() => setRevision((value) => value + 1)}
                      >
                        Retry
                      </button>
                    </div>
                  )}
                </div>
                <footer className="table-footer">
                  <span>
                    {loading
                      ? "Loading employees…"
                      : `Showing ${first}–${last} of ${total} employees`}
                  </span>
                  <div className="pager">
                    <label>
                      Rows per page{" "}
                      <select
                        value={query.page_size}
                        onChange={(event) => filter("page_size", Number(event.target.value))}
                      >
                        <option value="10">10</option>
                        <option value="25">25</option>
                        <option value="50">50</option>
                      </select>
                    </label>
                    <button
                      aria-label="Previous page"
                      disabled={query.page <= 1 || loading}
                      onClick={() =>
                        setQuery((current) => ({ ...current, page: current.page - 1 }))
                      }
                    >
                      ‹
                    </button>
                    <span>{loading ? "Page loading…" : `Page ${query.page} of ${totalPages}`}</span>
                    <button
                      aria-label="Next page"
                      disabled={query.page >= totalPages || loading}
                      onClick={() =>
                        setQuery((current) => ({ ...current, page: current.page + 1 }))
                      }
                    >
                      ›
                    </button>
                  </div>
                </footer>
              </section>
              <p className="page-footnote">
                Salary values are shown in USD for comparison. Edit an employee to view or change
                their native salary.
              </p>
            </>
          )}
        </div>
      </main>
      {formMode && (
        <EmployeeForm
          key={formMode.kind === "edit" ? formMode.employee.employee_id : "create"}
          mode={formMode}
          onClose={() => setFormMode(null)}
          onSaved={saved}
        />
      )}
    </div>
  );
}
