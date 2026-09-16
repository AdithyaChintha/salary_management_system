export type Employee = {
  id: number;
  employee_id: string;
  name: string;
  country: string;
  department: string;
  role: string;
  annual_salary_native: string;
  currency: string;
  salary_usd: string;
  is_active: boolean;
  deactivated_at: string | null;
  created_at: string;
  updated_at: string;
};

export type EmployeeInput = Pick<
  Employee,
  "employee_id" | "name" | "country" | "department" | "role" | "annual_salary_native" | "currency"
>;

export type EmployeePage = {
  items: Employee[];
  total: number;
  page: number;
  page_size: number;
};

export type EmployeeQuery = {
  search: string;
  country: string;
  department: string;
  is_active: string;
  min_salary_usd: string;
  max_salary_usd: string;
  page: number;
  page_size: number;
  sort_by: "name" | "employee_id" | "salary_usd" | "created_at";
  sort_order: "asc" | "desc";
};

const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Could not reach the API. Check that the backend is running.", 0);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.error?.details?.[0]?.message;
    const message = body?.error?.message || detail || `Request failed (${response.status}).`;
    throw new ApiError(detail && message === "Invalid request" ? detail : message, response.status);
  }
  return response.json() as Promise<T>;
}

export function listEmployees(query: EmployeeQuery, signal?: AbortSignal): Promise<EmployeePage> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== "") params.set(key, String(value));
  }
  return request<EmployeePage>(`/employees?${params.toString()}`, { signal });
}

export function createEmployee(input: EmployeeInput): Promise<Employee> {
  return request<Employee>("/employees", { method: "POST", body: JSON.stringify(input) });
}

export function updateEmployee(
  employeeId: string,
  input: Omit<EmployeeInput, "employee_id">,
): Promise<Employee> {
  return request<Employee>(`/employees/${encodeURIComponent(employeeId)}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function setEmployeeActive(employeeId: string, active: boolean): Promise<Employee> {
  return request<Employee>(
    `/employees/${encodeURIComponent(employeeId)}/${active ? "reactivate" : "deactivate"}`,
    { method: "POST" },
  );
}
