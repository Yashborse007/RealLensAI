import { fireEvent, render, screen } from "@testing-library/react";
import { ToastProvider, useToast } from "../context/ToastContext";

function ToastTrigger() {
  const { notify } = useToast();
  return (
    <button onClick={() => notify("Analysis completed.", "success")}>
      Notify
    </button>
  );
}

describe("ToastProvider", () => {
  it("announces and dismisses notifications", () => {
    render(
      <ToastProvider>
        <ToastTrigger />
      </ToastProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Notify" }));
    expect(screen.getByRole("status")).toHaveTextContent("Analysis completed.");

    fireEvent.click(screen.getByRole("button", { name: "Dismiss notification" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
