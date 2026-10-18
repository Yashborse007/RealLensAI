import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import LoginPage from "../pages/LoginPage";

const loginMock = vi.fn();

vi.mock("../context/AuthContext", () => ({
  useAuth: () => ({ login: loginMock }),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    loginMock.mockReset();
  });

  it("submits credentials and redirects to the dashboard on success", async () => {
    loginMock.mockResolvedValue({ success: true });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/dashboard" element={<div>Dashboard</div>} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/investigator email/i), {
      target: { value: "analyst@forensics.org" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "password123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in to portal/i }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith(
        "analyst@forensics.org",
        "password123",
      );
    });

    await waitFor(() => {
      expect(screen.getByText("Dashboard")).toBeInTheDocument();
    });
  });

  it("displays a validation error when authentication fails", async () => {
    loginMock.mockResolvedValue({
      success: false,
      error: "Invalid email or password.",
    });

    render(
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
        </Routes>
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/investigator email/i), {
      target: { value: "bad@forensics.org" },
    });
    fireEvent.change(screen.getByLabelText(/password/i), {
      target: { value: "bad-pass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /sign in to portal/i }));

    await waitFor(() => {
      expect(screen.getByText(/authentication error/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/invalid email or password/i)).toBeInTheDocument();
  });
});
