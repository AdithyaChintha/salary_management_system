import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { App } from "./App";
import {
  createEmployee,
  listEmployees,
  setEmployeeActive,
  updateEmployee,
  type Employee,
} from "./api/employees";

vi.mock("./api/employees", () => ({
  listEmployees: vi.fn(),
  createEmployee: vi.fn(),
  updateEmployee: vi.fn(),
  setEmployeeActive: vi.fn(),
}));

const employee: Employee = {
  id: 1,
  employee_id: "EMP-001",
  name: "Rahul Sharma",
  country: "IN",
  department: "Engineering",
  role: "Software Engineer",
  annual_salary_native: "5000000.00",
  currency: "INR",
  salary_usd: "60000.00",
  is_active: true,
  deactivated_at: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(listEmployees).mockResolvedValue({
    items: [employee],
    total: 1,
    page: 1,
    page_size: 10,
  });
  vi.mocked(createEmployee).mockResolvedValue(employee);
  vi.mocked(updateEmployee).mockResolvedValue(employee);
  vi.mocked(setEmployeeActive).mockResolvedValue(employee);
});

it("loads employees and sends filters and sorting to the server", async () => {
  render(<App />);
  expect(await screen.findByText("Rahul Sharma")).toBeInTheDocument();
  expect(vi.mocked(listEmployees).mock.calls[0][0]).toMatchObject({ is_active: "true", page: 1 });

  fireEvent.change(screen.getByLabelText("Filter by country"), { target: { value: "IN" } });
  await waitFor(() =>
    expect(vi.mocked(listEmployees).mock.lastCall?.[0]).toMatchObject({ country: "IN", page: 1 }),
  );

  fireEvent.click(screen.getByRole("button", { name: /salary \(usd\)/i }));
  await waitFor(() =>
    expect(vi.mocked(listEmployees).mock.lastCall?.[0]).toMatchObject({ sort_by: "salary_usd" }),
  );
});

it("sends search, status, and pagination changes to the server", async () => {
  const user = userEvent.setup();
  vi.mocked(listEmployees).mockResolvedValue({
    items: [employee],
    total: 23,
    page: 1,
    page_size: 10,
  });
  render(<App />);
  await screen.findByText("Rahul Sharma");
  await user.type(screen.getByLabelText("Search by name or employee ID"), "Rahul");
  await waitFor(() =>
    expect(vi.mocked(listEmployees).mock.lastCall?.[0]).toMatchObject({ search: "Rahul", page: 1 }),
  );
  await user.selectOptions(screen.getByLabelText("Filter by status"), "false");
  await waitFor(() =>
    expect(vi.mocked(listEmployees).mock.lastCall?.[0]).toMatchObject({ is_active: "false" }),
  );
  await user.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() =>
    expect(vi.mocked(listEmployees).mock.lastCall?.[0]).toMatchObject({ page: 2 }),
  );
});

it("creates an employee with currency derived from country", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("Rahul Sharma");
  await user.click(screen.getByRole("button", { name: /add employee/i }));
  const dialog = screen.getByRole("dialog");
  await user.type(within(dialog).getByLabelText("Employee ID"), "EMP-10001");
  await user.type(within(dialog).getByLabelText("Full name"), "Anita Rao");
  await user.selectOptions(within(dialog).getByLabelText("Country"), "IN");
  await user.type(within(dialog).getByLabelText("Role"), "Data Analyst");
  await user.type(within(dialog).getByLabelText(/annual salary/i), "1000000");
  expect(within(dialog).getByLabelText("Currency")).toHaveValue("INR");
  await user.click(within(dialog).getByRole("button", { name: "Add employee" }));
  await waitFor(() =>
    expect(createEmployee).toHaveBeenCalledWith(
      expect.objectContaining({
        employee_id: "EMP-10001",
        currency: "INR",
        country: "IN",
      }),
    ),
  );
});

it("keeps employee ID fixed during edit", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByText("Rahul Sharma");
  await user.click(screen.getByRole("button", { name: "Edit" }));
  const dialog = screen.getByRole("dialog");
  expect(within(dialog).getByLabelText("Employee ID")).toBeDisabled();
  await user.clear(within(dialog).getByLabelText("Full name"));
  await user.type(within(dialog).getByLabelText("Full name"), "Rahul S");
  await user.click(within(dialog).getByRole("button", { name: "Save changes" }));
  await waitFor(() =>
    expect(updateEmployee).toHaveBeenCalledWith(
      "EMP-001",
      expect.objectContaining({ name: "Rahul S" }),
    ),
  );
  expect(vi.mocked(updateEmployee).mock.calls[0][1]).not.toHaveProperty("employee_id");
});

it("shows the API conflict message in the employee form", async () => {
  const user = userEvent.setup();
  vi.mocked(createEmployee).mockRejectedValue(new Error("EMP-10001 already exists"));
  render(<App />);
  await screen.findByText("Rahul Sharma");
  await user.click(screen.getByRole("button", { name: /add employee/i }));
  const dialog = screen.getByRole("dialog");
  await user.type(within(dialog).getByLabelText("Employee ID"), "EMP-10001");
  await user.type(within(dialog).getByLabelText("Full name"), "Anita Rao");
  await user.type(within(dialog).getByLabelText("Role"), "Analyst");
  await user.type(within(dialog).getByLabelText("Annual salary"), "80000");
  await user.click(within(dialog).getByRole("button", { name: "Add employee" }));
  expect(await within(dialog).findByRole("alert")).toHaveTextContent("EMP-10001 already exists");
});

it("confirms deactivation and allows inactive employees to be reactivated", async () => {
  const user = userEvent.setup();
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
  const view = render(<App />);
  await screen.findByText("Rahul Sharma");
  await user.click(screen.getByRole("button", { name: "Deactivate" }));
  expect(confirm).toHaveBeenCalled();
  await waitFor(() => expect(setEmployeeActive).toHaveBeenCalledWith("EMP-001", false));
  view.unmount();
  vi.mocked(listEmployees).mockResolvedValue({
    items: [{ ...employee, is_active: false }],
    total: 1,
    page: 1,
    page_size: 10,
  });
  render(<App />);
  await screen.findByText("Rahul Sharma");
  await user.click(screen.getByRole("button", { name: "Reactivate" }));
  await waitFor(() => expect(setEmployeeActive).toHaveBeenCalledWith("EMP-001", true));
  confirm.mockRestore();
});

it("shows empty and API error states", async () => {
  vi.mocked(listEmployees).mockResolvedValueOnce({ items: [], total: 0, page: 1, page_size: 10 });
  const view = render(<App />);
  expect(await screen.findByText("No employees found")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  view.unmount();
  vi.mocked(listEmployees).mockRejectedValueOnce(new Error("Backend unavailable"));
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Backend unavailable");
});
