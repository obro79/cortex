import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "assets/hackathon/scoreboard.svg");
mkdirSync(dirname(output), { recursive: true });
const rows = [
  ["Slack", "3"], ["Google Drive", "2"], ["Linear", "2"],
  ["GitHub", "1"], ["Jira", "1"], ["Repository docs", "1"],
];
const rowSvg = rows.map(([name, count], index) => {
  const y = 314 + index * 61;
  return `<text x="120" y="${y}" class="name">${name}</text><rect x="1110" y="${y - 34}" width="180" height="38" rx="19" fill="#203e69"/><text x="1200" y="${y - 7}" class="count" text-anchor="middle">${count}</text>`;
}).join("");
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000" role="img" aria-labelledby="title desc">
<title id="title">Cortex hackathon synthetic fixture scoreboard</title><desc id="desc">Exact count scoreboard: ten synthetic records, three media source files, two captions and one transcript. Not live.</desc>
<style>text{font-family:Arial,sans-serif;fill:#edf4ff}.title{font-size:52px;font-weight:700}.sub{font-size:23px;fill:#b7c6dd}.name{font-size:27px;font-weight:700}.count{font-size:23px;font-weight:700}.stat{font-size:31px;font-weight:700}.statSmall{font-size:19px;fill:#c5d4ea}.stamp{font-size:24px;font-weight:700;letter-spacing:2px}</style>
<rect width="1600" height="1000" fill="#071225"/><rect x="1060" y="70" width="410" height="60" rx="30" fill="#ffcf5c"/><text x="1265" y="109" text-anchor="middle" fill="#071225" class="stamp">SYNTHETIC • NOT LIVE</text>
<text x="120" y="125" class="title">Fixture corpus scoreboard</text><text x="120" y="165" class="sub">Exact demo inventory — source shapes, not active provider connections</text>
<rect x="90" y="220" width="1240" height="500" rx="24" fill="#122544" stroke="#3c659e"/>${rowSvg}
<rect x="90" y="760" width="390" height="150" rx="24" fill="#1c4d58"/><text x="125" y="820" class="stat">10 source records</text><text x="125" y="858" class="statSmall">fixed, deterministic fixtures</text>
<rect x="515" y="760" width="390" height="150" rx="24" fill="#3a315d"/><text x="550" y="820" class="stat">3 media-source files</text><text x="550" y="858" class="statSmall">part of the ten source records</text>
<rect x="940" y="760" width="390" height="150" rx="24" fill="#573a31"/><text x="975" y="820" class="stat">2 captions + 1 transcript</text><text x="975" y="858" class="statSmall">derived artifacts; not extra records</text>
<text x="120" y="955" class="sub">No live OAuth, provider APIs, customer data, or production indexing is represented in this scoreboard.</text></svg>`;
writeFileSync(output, svg);
console.log(`Wrote ${output}`);
