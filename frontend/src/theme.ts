import type { ThemeConfig } from "antd";

export const ACCENT = "#2f6f8f";

/** Palette used for stacked score-composition bars, tinted from the accent. */
export const SERIES_COLORS = [
  "#2f6f8f",
  "#4a9ab5",
  "#7bbfcf",
  "#a8d8e0",
  "#cbe9ee",
];

export const theme: ThemeConfig = {
  token: {
    colorPrimary: ACCENT,
    colorError: "#b3402f",
    colorLink: ACCENT,
    colorBgLayout: "#f6f7f9",
    colorText: "#1c2733",
    borderRadius: 6,
    fontFamily: 'ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif',
  },
  components: {
    Layout: {
      headerBg: "#ffffff",
      headerHeight: 56,
      headerPadding: "0 20px",
      siderBg: "#ffffff",
      bodyBg: "#f6f7f9",
    },
  },
};
