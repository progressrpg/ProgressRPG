import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToastProvider } from "./ToastContext";
import { useToast } from "../hooks/useToast";
import { useFeatureFlag } from "../hooks/useFeatureFlag";

vi.mock("../hooks/useFeatureFlag", () => ({ useFeatureFlag: vi.fn() }));
vi.mock("../components/Toast/ToastManager", () => ({
  default: ({ messages }: { messages: { id: string; message: string }[] }) => (
    <div data-testid="toast-manager">{messages.map((m) => m.message).join(",")}</div>
  ),
}));

const mockedUseFeatureFlag = useFeatureFlag as ReturnType<typeof vi.fn>;

function Consumer() {
  const { toasts, showToast } = useToast();
  return (
    <div>
      <span data-testid="count">{toasts.length}</span>
      <button onClick={() => showToast("hello")}>show</button>
    </div>
  );
}

describe("ToastProvider", () => {
  it("starts with no toasts", () => {
    mockedUseFeatureFlag.mockReturnValue(false);

    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    );

    expect(screen.getByTestId("count")).toHaveTextContent("0");
  });

  it("adds a toast via showToast", () => {
    mockedUseFeatureFlag.mockReturnValue(false);

    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    );

    act(() => {
      screen.getByText("show").click();
    });

    expect(screen.getByTestId("count")).toHaveTextContent("1");
  });

  it("does not render ToastManager when the toastsFeature flag is off", () => {
    mockedUseFeatureFlag.mockReturnValue(false);

    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    );

    expect(screen.queryByTestId("toast-manager")).not.toBeInTheDocument();
  });

  it("renders ToastManager with active toasts when the toastsFeature flag is on", () => {
    mockedUseFeatureFlag.mockReturnValue(true);

    render(
      <ToastProvider>
        <Consumer />
      </ToastProvider>
    );

    act(() => {
      screen.getByText("show").click();
    });

    expect(screen.getByTestId("toast-manager")).toHaveTextContent("hello");
  });
});

describe("useToast", () => {
  it("throws when used outside a ToastProvider", () => {
    const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    function BareConsumer() {
      useToast();
      return null;
    }

    expect(() => render(<BareConsumer />)).toThrow(
      "useToast must be used within a ToastProvider"
    );

    consoleErrorSpy.mockRestore();
  });
});
