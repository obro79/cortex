import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cortex: {
          bg: "#080a0f",
          panel: "#10141d",
          border: "#252b36",
          ink: "#f7f8fb",
          muted: "#9ba4b5",
          green: "#75d6a3",
          amber: "#f0c36a",
          blue: "#89b4ff",
        },
      },
    },
  },
  plugins: [],
};

export default config;
