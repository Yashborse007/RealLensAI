import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import RegisterPage from "../pages/RegisterPage";

const registerMock = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ register: registerMock }),
}));

describe("RegisterPage", () => {
  beforeEach(() => {
    registerMock.mockReset();
  });

  it("registers with a Gmail address and redirects to the dashboard", async () => {
    registerMock.mockResolvedValue({ success: true });

    render(
      <MemoryRouter initialEntries={["/register"]}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/full name/i), {
      target: { value: "RealLens Analyst" },
    });
    fireEvent.change(screen.getByLabelText(/email address/i), {
      target: { value: "analyst@gmail.com" },
    });
    fireEvent.change(screen.getByLabelText(/create password/i), {
      target: { value: "SafePass123" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: /complete registration/i }),
    );

    await waitFor(() => {
      expect(registerMock).toHaveBeenCalledWith(
        "RealLens Analyst",
        "analyst@gmail.com",
        "SafePass123",
      );
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  it("does not expose public administrator registration", () => {
    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>,
    );

    expect(screen.queryByLabelText(/account role/i)).not.toBeInTheDocument();
  });
});
