/** Build an editable, dependency-free 16:9 PowerPoint deck for the fixture demo. */
import { execFileSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const output = resolve(root, "deliverables/slides/cortex-hackathon-demo.pptx");
const esc = (value) => String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const slides = [
  ["Cortex", ["Evidence-first context for fragmented work", "HACKATHON DEMO • SYNTHETIC FIXTURES • NOT LIVE"]],
  ["The problem", ["Decisions are split across messages, docs, tickets, code, and media.", "Search finds fragments. Teams still need the why, the source, and the confidence."]],
  ["The Cortex promise", ["Normalize work context into retrievable evidence.", "Answer a cross-source question — then show the supporting source, excerpt, and fixture route."]],
  ["Demo corpus: exact & repeatable", ["10 synthetic source records", "Slack 3 • Google Drive 2 • Linear 2", "GitHub 1 • Jira 1 • Repository docs 1", "3 media-source files → 2 captions + 1 transcript (derived, not extra records)"]],
  ["MCP-first, control-plane companion", ["Codex, Claude, and Cursor use Cortex through an MCP boundary; a local UI helps inspect evidence and health.", "Postgres is canonical. Hosted Qdrant is the intended durable vector-index target — not deployed or proven here."]],
  ["The demo moment", ["Ask for the decision and rationale across source shapes.", "Reveal evidence rows: source label, fixture ID, supporting excerpt, and route back to fixture context."]],
  ["Why media matters", ["Media files receive derived captions or transcripts so their context can join the same evidence path.", "Fixture corpus: 3 media-source files, 2 captions, 1 transcript."]],
  ["What we proved — and what we did not", ["Proved: repeatable source → evidence → answer walkthrough on controlled fixtures.", "Not proved: live connectors, realtime sync, production permissions, or retrieval quality at customer scale.", "Cortex: make answers inspectable, not merely searchable."]],
];
const contentTypes = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>${slides.map((_, i) => `<Override PartName="/ppt/slides/slide${i + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`).join("")}</Types>`;
const rels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/></Relationships>`;
const presRels = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">${slides.map((_, i) => `<Relationship Id="rId${i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${i + 1}.xml"/>`).join("")}</Relationships>`;
const presentation = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldIdLst>${slides.map((_, i) => `<p:sldId id="${256 + i}" r:id="rId${i + 1}"/>`).join("")}</p:sldIdLst><p:sldSz cx="12192000" cy="6858000" type="screen16x9"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>`;
function shape(x, y, w, h, text, size, color = "EAF2FF", bold = false) {
  return `<p:sp><p:nvSpPr><p:cNvPr id="${Math.floor(x + y + w)}" name="Text"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="${x}" y="${y}"/><a:ext cx="${w}" cy="${h}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></p:spPr><p:txBody><a:bodyPr wrap="square"/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="${size}" b="${bold ? 1 : 0}"><a:solidFill><a:srgbClr val="${color}"/></a:solidFill></a:rPr><a:t>${esc(text)}</a:t></a:r><a:endParaRPr lang="en-US"/></a:p></p:txBody></p:sp>`;
}
function slideXml(title, lines, index) {
  const titleColor = index === 0 ? "68D6B0" : "EAF2FF";
  const body = lines.map((line, i) => shape(900000, 2450000 + i * 800000, 10400000, 600000, line, 2200, i === lines.length - 1 && index === 0 ? "FFCF5C" : "C6D5EC", false)).join("");
  const bg = `<p:sp><p:nvSpPr><p:cNvPr id="1" name="Background"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="081225"/></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>`;
  const footer = shape(900000, 6260000, 10400000, 300000, `CORTEX  /  FIXTURE DEMO  /  ${String(index + 1).padStart(2, "0")}`, 950, "7795BE", true);
  return `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="0" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>${bg}${shape(900000, 850000, 10400000, 900000, title, 4000, titleColor, true)}${body}${footer}</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>`;
}
const temp = mkdtempSync(join(tmpdir(), "cortex-pptx-"));
try {
  mkdirSync(join(temp, "_rels")); mkdirSync(join(temp, "ppt/_rels"), { recursive: true }); mkdirSync(join(temp, "ppt/slides"), { recursive: true });
  writeFileSync(join(temp, "[Content_Types].xml"), contentTypes); writeFileSync(join(temp, "_rels/.rels"), rels);
  writeFileSync(join(temp, "ppt/presentation.xml"), presentation); writeFileSync(join(temp, "ppt/_rels/presentation.xml.rels"), presRels);
  slides.forEach(([title, lines], i) => writeFileSync(join(temp, `ppt/slides/slide${i + 1}.xml`), slideXml(title, lines, i)));
  mkdirSync(dirname(output), { recursive: true }); rmSync(output, { force: true });
  execFileSync("zip", ["-q", "-r", output, "."], { cwd: temp });
  console.log(`Wrote ${output} (${slides.length} editable 16:9 slides)`);
} finally { rmSync(temp, { recursive: true, force: true }); }
