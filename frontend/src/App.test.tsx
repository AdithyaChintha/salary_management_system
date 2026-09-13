import { render, screen } from "@testing-library/react";

import { App } from "./App";

describe("App", () => {
  it("renders the scaffold message", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: /salary management system/i })).toBeInTheDocument();
  });
});

