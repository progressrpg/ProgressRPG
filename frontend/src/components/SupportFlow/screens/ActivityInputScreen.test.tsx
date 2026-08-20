// SupportFlow/screens/ActivityInputScreen.test.tsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render as rtlRender, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TamaguiProvider } from "tamagui";
import ActivityInputScreen from "./ActivityInputScreen";
import tamaguiConfig from "../../../../tamagui.config";

// ActivityInputScreen renders Tabs (#584), which needs a TamaguiProvider
// ancestor - unlike Radix's Tabs.Root, it isn't usable standalone. The app
// root (src/main.tsx) provides this in production; tests need their own.
function render(...args: Parameters<typeof rtlRender>) {
  const [ui, options] = args;
  return rtlRender(ui, {
    wrapper: ({ children }) => (
      <TamaguiProvider config={tamaguiConfig} defaultTheme="light">
        {children}
      </TamaguiProvider>
    ),
    ...options,
  });
}

const mockUseFeatureFlag = vi.fn();

vi.mock("../../../hooks/useFeatureFlag", () => ({
  useFeatureFlag: (flag: string) => mockUseFeatureFlag(flag),
}));

vi.mock("../../../hooks/useTasks", () => ({
  useTasks: () => ({
    data: [
      { id: 1, name: "Water the plants", is_complete: false, completed_at: null },
      { id: 2, name: "Reply to email", is_complete: false, completed_at: null },
    ],
  }),
}));

describe("ActivityInputScreen", () => {
  describe("priority_three preset, with the tasks feature enabled", () => {
    beforeEach(() => {
      mockUseFeatureFlag.mockReturnValue(true);
    });

    it("defaults to the 'From memory' tab", () => {
      render(<ActivityInputScreen activityPresetId="priority_three" />);

      expect(screen.getByRole("tab", { name: "From memory" })).toHaveAttribute("aria-selected", "true");
      expect(screen.getByRole("tab", { name: "My tasks" })).toHaveAttribute("aria-selected", "false");
      expect(screen.getByLabelText("Task option 1")).toBeInTheDocument();
    });

    it("switches to the 'My tasks' tab, showing incomplete tasks and hiding the memory panel", async () => {
      const user = userEvent.setup();
      render(<ActivityInputScreen activityPresetId="priority_three" />);

      await user.click(screen.getByRole("tab", { name: "My tasks" }));

      expect(screen.getByRole("tab", { name: "My tasks" })).toHaveAttribute("aria-selected", "true");
      expect(screen.getByText("Water the plants")).toBeInTheDocument();
      expect(screen.getByText("Reply to email")).toBeInTheDocument();
      expect(screen.queryByLabelText("Task option 1")).not.toBeInTheDocument();
    });

    it("wires the ARIA tab/tabpanel relationship", () => {
      render(<ActivityInputScreen activityPresetId="priority_three" />);

      const tab = screen.getByRole("tab", { name: "From memory" });
      const panel = screen.getByRole("tabpanel");

      expect(tab.getAttribute("aria-controls")).toBe(panel.getAttribute("id"));
      expect(panel.getAttribute("aria-labelledby")).toBe(tab.getAttribute("id"));
    });
  });

  it("does not render tabs when the tasks feature is disabled", () => {
    mockUseFeatureFlag.mockReturnValue(false);

    render(<ActivityInputScreen activityPresetId="priority_three" />);

    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });
});
