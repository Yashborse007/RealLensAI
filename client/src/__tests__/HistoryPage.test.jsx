import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import HistoryPage from "../pages/HistoryPage";

const getUserAnalysesMock = vi.hoisted(() => vi.fn());

vi.mock("../services/api", () => ({
  getUserAnalyses: getUserAnalysesMock,
}));

describe("HistoryPage", () => {
  beforeEach(() => {
    getUserAnalysesMock.mockReset();
    getUserAnalysesMock.mockResolvedValue({
      data: [
        {
          id: "ana_1",
          filename: "sample_image.png",
          mediaType: "image",
          prediction: "REAL",
          confidence: 0.96,
          createdAt: "2024-05-01T10:00:00Z",
        },
        {
          id: "ana_2",
          filename: "sample_video.mp4",
          mediaType: "video",
          prediction: "FAKE",
          confidence: 0.88,
          createdAt: "2024-05-02T11:00:00Z",
        },
      ],
      totalPages: 1,
    });
  });

  it("renders analysis records and applies the selected media filter", async () => {
    render(
      <MemoryRouter>
        <HistoryPage />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText("sample_image.png")).toBeInTheDocument();
    });

    fireEvent.change(screen.getAllByRole("combobox")[0], {
      target: { value: "video" },
    });

    await waitFor(() => {
      expect(getUserAnalysesMock).toHaveBeenLastCalledWith(
        expect.objectContaining({ mediaType: "video" }),
      );
    });
  });
});
