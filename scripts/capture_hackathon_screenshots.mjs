import { mkdir } from "node:fs/promises";
import { createRequire } from "node:module";
import { resolve } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const baseUrl = process.env.CORTEX_DEMO_URL ?? "http://127.0.0.1:8010";
const outputDirectory = resolve("deliverables/screenshots");

await mkdir(outputDirectory, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1080 } });

try {
  await page.goto(`${baseUrl}/case-study`, { waitUntil: "networkidle" });
  await page.screenshot({
    path: resolve(outputDirectory, "case-study-hero.png"),
    fullPage: false,
  });

  const evidenceSection = page
    .getByRole("heading", { name: "Evidence", exact: true })
    .locator("xpath=..");
  await evidenceSection.screenshot({
    path: resolve(outputDirectory, "case-study-evidence.png"),
  });
} finally {
  await browser.close();
}
