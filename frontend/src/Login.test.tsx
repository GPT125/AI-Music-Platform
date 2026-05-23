import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import Login from "./Login";

vi.mock("./api", () => ({
  api: {
    googleConfig: () => Promise.resolve({ configured: false, client_id: "" }),
    googleStartUrl: () => "/api/auth/google/start",
  },
}));

describe("Login", () => {
  it("shows Google-only sign-in", async () => {
    render(<Login />);
    expect(await screen.findByText("Sign in or sign up with Google")).toBeInTheDocument();
  });
});
