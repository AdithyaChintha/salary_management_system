import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import { createEmployee, updateEmployee, type Employee, type EmployeeInput } from "./api/employees";
import { COUNTRIES, DEPARTMENTS } from "./employee-data";

export type FormMode = { kind: "create" } | { kind: "edit"; employee: Employee };

const EMPTY_FORM: EmployeeInput = {
  employee_id: "",
  name: "",
  country: "US",
  department: "Engineering",
  role: "",
  annual_salary_native: "",
  currency: "USD",
};

export function EmployeeForm({
  mode,
  onClose,
  onSaved,
}: {
  mode: FormMode;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<EmployeeInput>(() =>
    mode.kind === "edit"
      ? {
          employee_id: mode.employee.employee_id,
          name: mode.employee.name,
          country: mode.employee.country,
          department: mode.employee.department,
          role: mode.employee.role,
          annual_salary_native: mode.employee.annual_salary_native,
          currency: mode.employee.currency,
        }
      : EMPTY_FORM,
  );
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const dialogRef = useRef<HTMLElement>(null);

  useEffect(() => {
    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialogRef.current?.querySelector<HTMLInputElement>("input:not(:disabled)")?.focus();
    return () => previouslyFocused?.focus();
  }, []);

  function handleDialogKeyDown(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Escape" && !saving) {
      onClose();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(
      'button:not(:disabled), input:not(:disabled), select:not(:disabled), [tabindex]:not([tabindex="-1"])',
    );
    if (!focusable?.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function change(field: keyof EmployeeInput, value: string) {
    setError("");
    setForm((current) =>
      field === "country"
        ? {
            ...current,
            country: value,
            currency: COUNTRIES.find((country) => country.code === value)?.currency ?? "",
          }
        : { ...current, [field]: value },
    );
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = {
      ...form,
      employee_id: form.employee_id.trim(),
      name: form.name.trim(),
      role: form.role.trim(),
    };
    if (!input.employee_id || !input.name || !input.role) {
      setError("Employee ID, name, and role are required.");
      return;
    }
    if (
      !Number.isFinite(Number(input.annual_salary_native)) ||
      Number(input.annual_salary_native) <= 0
    ) {
      setError("Annual salary must be greater than zero.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (mode.kind === "create") await createEmployee(input);
      else {
        await updateEmployee(mode.employee.employee_id, {
          name: input.name,
          country: input.country,
          department: input.department,
          role: input.role,
          annual_salary_native: input.annual_salary_native,
          currency: input.currency,
        });
      }
      onSaved();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save the employee.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="form-title"
        onKeyDown={handleDialogKeyDown}
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">EMPLOYEE DETAILS</span>
            <h2 id="form-title">{mode.kind === "create" ? "Add employee" : "Edit employee"}</h2>
            <p>
              {mode.kind === "create"
                ? "Create a new salary record."
                : "Update this employee’s current details."}
            </p>
          </div>
          <button type="button" className="icon-button" aria-label="Close form" onClick={onClose}>
            ×
          </button>
        </div>
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Employee ID
              <input
                aria-label="Employee ID"
                value={form.employee_id}
                onChange={(event) => change("employee_id", event.target.value)}
                disabled={mode.kind === "edit"}
                required
                maxLength={50}
                placeholder="EMP-10001"
              />
              {mode.kind === "edit" && <small>Employee ID cannot be changed.</small>}
            </label>
            <label>
              Full name
              <input
                aria-label="Full name"
                value={form.name}
                onChange={(event) => change("name", event.target.value)}
                required
                maxLength={200}
                placeholder="e.g. Rahul Sharma"
              />
            </label>
            <label>
              Country
              <select
                aria-label="Country"
                value={form.country}
                onChange={(event) => change("country", event.target.value)}
              >
                {COUNTRIES.map((country) => (
                  <option key={country.code} value={country.code}>
                    {country.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Currency
              <input aria-label="Currency" value={form.currency} readOnly />
              <small>Set automatically from country.</small>
            </label>
            <label>
              Department
              <select
                aria-label="Department"
                value={form.department}
                onChange={(event) => change("department", event.target.value)}
              >
                {DEPARTMENTS.map((department) => (
                  <option key={department} value={department}>
                    {department}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Role
              <input
                aria-label="Role"
                value={form.role}
                onChange={(event) => change("role", event.target.value)}
                required
                maxLength={200}
                placeholder="e.g. Software Engineer"
              />
            </label>
            <label className="wide-field">
              Annual salary ({form.currency})
              <input
                aria-label="Annual salary"
                type="number"
                min="0.01"
                step="0.01"
                value={form.annual_salary_native}
                onChange={(event) => change("annual_salary_native", event.target.value)}
                required
                placeholder="0.00"
              />
              <small>The backend calculates the USD amount.</small>
            </label>
          </div>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="modal-actions">
            <button
              type="button"
              className="button button-quiet"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </button>
            <button type="submit" className="button button-primary" disabled={saving}>
              {saving ? "Saving…" : mode.kind === "create" ? "Add employee" : "Save changes"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
