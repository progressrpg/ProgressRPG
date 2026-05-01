import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import Form from "./Form";

describe("Form", () => {
  it("shows required validation after blur", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn((event) => event.preventDefault());

    render(
      <Form
        title="Test form"
        onSubmit={onSubmit}
        fields={[
          {
            name: "email",
            label: "Email",
            type: "email",
            value: "",
            onChange: vi.fn(),
            required: true,
          },
        ]}
      />
    );

    const input = screen.getByLabelText(/email/i);
    await user.click(input);
    await user.tab();

    expect(screen.getByText("This field is required")).toBeInTheDocument();
  });

  it("prefers server field errors over local validation messages", () => {
    render(
      <Form
        title="Test form"
        onSubmit={(event) => event.preventDefault()}
        fieldErrors={{ email: ["Email already exists"] }}
        fields={[
          {
            name: "email",
            label: "Email",
            type: "email",
            value: "",
            onChange: vi.fn(),
            required: true,
          },
        ]}
      />
    );

    expect(screen.getByText("Email already exists")).toBeInTheDocument();
    expect(screen.queryByText("This field is required")).not.toBeInTheDocument();
  });

  it("disables the submit button while submitting", () => {
    render(
      <Form
        title="Submitting form"
        onSubmit={(event) => event.preventDefault()}
        isSubmitting
      />
    );

    expect(screen.getByRole("button", { name: "Submitting form" })).toBeDisabled();
    expect(screen.getByText("Submitting…")).toBeInTheDocument();
  });
});
