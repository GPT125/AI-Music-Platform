import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./api", () => ({
  api: {
    me: vi.fn().mockRejectedValue(new Error("no session")),
    instruments: vi.fn().mockResolvedValue({ instruments: [] }),
  },
}));

describe("App", () => {
  it("shows private beta login when unauthenticated", async () => {
    render(<App />);
    expect(await screen.findByText("Private beta login")).toBeInTheDocument();
  });
});

