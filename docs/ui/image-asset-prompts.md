# Cortex Image Asset Prompts

This document plans GPT-generated bitmap assets for the Cortex landing page and
later app surfaces. It uses the existing UI planning docs as source material and
keeps product UI panels separate from decorative or editorial imagery.

Generated images should make Cortex feel specific to agent-context work:
retrieval, evidence, freshness, permissions, MCP, CLI, UI, Slack, GitHub,
Linear, and repo docs. They should not recreate Linear wording, screenshots,
claims, layout, or brand assets.

## Visual Principles

- Product truth first: visuals should show a workflow state, not abstract
  knowledge management metaphors.
- Keep UI screenshots in CSS: anything with readable text, controls, tables,
  citations, or provider status should be built as product UI panels instead of
  generated as a bitmap.
- Use generated bitmaps for atmosphere, thumbnails, depth layers, and editorial
  section art that supports CSS product panels.
- Make the scene recognizably Cortex: agent prompts, cited evidence, source
  objects, freshness markers, permission decisions, and workspace scope should
  appear as motifs.
- Avoid generic SaaS tropes: no floating dashboards, glassmorphism data clouds,
  vague AI brains, neon network globes, or smiling office people.
- Keep the tone quiet and premium: restrained contrast, crisp geometry, dense
  technical detail, and minimal ornament.
- Use fictional content only: no real company names, real user names, real issue
  IDs, real Slack messages, real repository names, or customer logos.
- Treat provider names as labels in CSS, not generated logo art. If a bitmap
  needs source systems, use neutral source icons or generic document shapes.
- Maintain legal distance from Linear: numbered chapters and figure labels are
  acceptable as page structure, but image composition, copy, product screens,
  icons, and claims must be original to Cortex.

## Global Style Tokens For Prompts

Use this shared style language in every image prompt unless a prompt overrides
it:

- Style: precise editorial product photography blended with clean technical UI
  illustration; realistic lighting; crisp but not photorealistic enough to look
  like a copied app screenshot.
- Palette: near-white and graphite base, with restrained accents in green,
  cyan, amber, and muted red for source health, freshness, and permission
  signals.
- Texture: subtle paper grain, faint monitor glow, soft shadowing, no gradients
  as the main subject.
- Typography: no readable body copy inside generated images; any labels should
  be abstract bars or short placeholder marks, with real text rendered in CSS.
- Composition: leave safe negative space for CSS overlays and figure labels.

## Landing Asset Inventory

### 1.0 Cortex

Primary visual: `FIG. 1.1` product-system map.

- Build as CSS/product UI: the engineer prompt, access path chips, Cortex router
  node, source nodes, connector lines, and cited context bundle. These need real
  labels and responsive behavior.
- Generate as bitmap: a subtle desktop workbench background behind the system
  map, plus faint source-object silhouettes that make the hero feel grounded.

Prompt draft:

```text
Create a 2400x1400 hero background image, 12:7 aspect ratio, for a product
website about an agent-context router called Cortex. Style is quiet premium
technical editorial, near-white and graphite workspace, restrained cyan, green,
amber, and muted red accents. Subject: a shallow-depth desktop scene with a
large blank central area reserved for a CSS-built product-system map, faint
out-of-focus source object silhouettes around the edges, subtle monitor glow,
thin cable-like routing lines, and abstract document cards suggesting chat
threads, pull requests, issues, and repo docs without logos or readable text.
Keep the center clean for UI overlay. Avoid: Linear app screenshots, Linear
layout, copied product claims, real logos, real company names, readable text,
generic AI brain imagery, neon network globes, glassmorphism dashboards,
people, mascots, and decorative blobs. Intended placement: landing section 1.0
behind FIG. 1.1 CSS product-system map.
```

Secondary visual: source-system detail strip below the hero or between 1.0 and
1.1.

- Build as CSS/product UI: provider labels and mode chips.
- Generate as bitmap: close-up crop of abstract evidence fragments.

Prompt draft:

```text
Create a 1800x520 horizontal detail strip, 45:13 aspect ratio. Style is clean
technical macro photography with a subtle editorial product feel. Subject:
layered abstract evidence fragments on a light surface: small unlabeled chat
message blocks, code diff shapes, issue-card outlines, architecture-document
pages, timestamp markers, lock markers, and citation pins. Use graphite lines
with sparse cyan, green, amber, and muted red accents. No readable text; use
short abstract marks only. Avoid: copied Linear cards, real provider logos,
exact app screenshots, fake marketing copy, customer quotes, human figures,
abstract AI symbols, and rainbow gradients. Intended placement: transitional
asset near landing section 1.0 to reinforce connected sources and evidence.
```

### 1.1 Ask

Primary visual: `FIG. 1.2` prompt-to-agent panel.

- Build as CSS/product UI: query input, user prompt, agent decision state, MCP,
  CLI, and UI chips.
- Generate as bitmap: a focused background plate that suggests a terminal and
  editor environment without readable code.

Prompt draft:

```text
Create a 1600x1000 image, 8:5 aspect ratio, for a section about asking an
agent for company context before changing code. Style is precise, calm,
technical editorial with a light graphite UI environment. Subject: an angled
desk-level composition with an empty prompt panel area in the lower left, a
softly blurred terminal-like surface, an editor-like pane made of abstract code
lines, and a small routing indicator pointing toward a blank space where the
Cortex UI will be rendered in CSS. Use sparse cyan and green highlights for
"ready" signals and muted amber for caution. Avoid: readable prompt text,
readable code, Linear UI, exact Linear layout, copied wording, real app logos,
generic chatbot bubbles, humanoid robots, dramatic sci-fi lighting, and dark
dashboard walls. Intended placement: landing section 1.1 behind or adjacent to
the CSS prompt-to-agent product panel.
```

Optional small asset: mode-chip icon texture for MCP, CLI, and UI access paths.

- Build as CSS/product UI: the chips and labels.
- Generate as bitmap: not recommended unless a very small non-readable texture
  is needed. Prefer icons in CSS.

### 1.2 Retrieve

Primary visual: `FIG. 1.3` retrieval in progress.

- Build as CSS/product UI: provider columns, object cards, source counts,
  freshness rail, and excluded result states.
- Generate as bitmap: four neutral source-object thumbnails that can sit inside
  or behind CSS cards without readable text.

Prompt draft:

```text
Create a 2000x1200 image, 5:3 aspect ratio, composed as four separate neutral
source-object thumbnail panels on one canvas with clear gutters between them.
Style is crisp editorial UI illustration with realistic paper and screen
materials. Subject: panel 1 suggests a chat thread through stacked message
blocks; panel 2 suggests a pull request through code diff stripes and commit
dots; panel 3 suggests an issue through status pills and checklist shapes;
panel 4 suggests a repo architecture doc through page sections and small diagram
nodes. Use no readable text and no provider logos. Accent colors should differ
slightly by source but stay restrained: cyan, green, amber, and graphite.
Avoid: Linear issue screenshots, Linear wording, actual Slack/GitHub/Linear
logos, real issue IDs, copied interface chrome, generic dashboard charts, AI
brain graphics, people, and over-polished stock icons. Intended placement:
landing section 1.2 as bitmap thumbnails inside the CSS retrieval columns.
```

Secondary visual: retrieval beam or source-to-context background layer.

- Build as CSS/product UI: live statuses and counts.
- Generate as bitmap: faint motion-like connection lines behind CSS provider
  columns.

Prompt draft:

```text
Create a 1800x900 background layer, 2:1 aspect ratio. Style is subtle technical
cartography on a light graphite-tinted background. Subject: fine routing paths
flowing from four side clusters into a single empty central bundle area, with
tiny abstract tokens, timestamp dots, lock marks, and citation pins traveling
along the paths. Leave the central 55 percent of the image low-detail so a CSS
retrieval panel can be placed on top. Avoid: neon data tunnels, generic network
globes, Linear page composition, readable text, real logos, brand colors copied
from providers, people, and decorative gradient blobs. Intended placement:
landing section 1.2 behind FIG. 1.3 retrieval UI.
```

### 1.3 Verify

Primary visual: `FIG. 1.4` evidence pack inspector.

- Build as CSS/product UI: original query, citation cards, source coverage,
  freshness, permission exclusions, source links, and agent trace links.
- Generate as bitmap: source-truth artifact surface, such as a calm evidence
  workspace background or citation detail thumbnails.

Prompt draft:

```text
Create a 1700x1100 image, 17:11 aspect ratio, for a product section about
verifying an answer with source truth. Style is quiet premium technical
editorial, high clarity, near-white surface with graphite UI fragments and
restrained signal colors. Subject: a layered evidence workspace with abstract
citation cards, tiny source pins, timestamp chips, lock and scope indicators,
and a faint right-side inspection rail area. Make all text unreadable placeholder
marks. Leave a large clean rectangle in the center for a CSS-built evidence pack
inspector. Avoid: Linear screenshots, copied issue card design, real provider
logos, legal claims, exact product claims, "AI magic" imagery, generic analytics
charts, people, and dark sci-fi styling. Intended placement: landing section
1.3 behind FIG. 1.4 evidence inspector.
```

Optional asset: permission-exclusion texture.

- Build as CSS/product UI: warnings and exclusion copy.
- Generate as bitmap: small non-text visual used as an empty-state accent.

Prompt draft:

```text
Create a 900x700 image, 9:7 aspect ratio, with transparent-feeling light
background for an empty-state accent about permission-aware exclusions. Style is
minimal technical editorial. Subject: three abstract document cards partially
masked by a soft scope boundary, small lock marks, muted amber and red status
dots, and one visible citation pin outside the boundary. No readable text. Avoid:
security shield cliches, padlock hero icons, Linear UI, real logos, real user
names, warning-heavy alarm styling, and dramatic red lighting. Intended
placement: small supporting visual in landing section 1.3 or Evidence Viewer
empty states.
```

### 1.4 Build

Primary visual: `FIG. 1.5` context bundle handed back to an agent.

- Build as CSS/product UI: Cortex response, citations, agent working plan,
  changed code or PR preparation panel, and labels for fresh, cited,
  workspace-scoped, and permission-aware.
- Generate as bitmap: a focused implementation environment background that
  makes the CSS panels feel embedded in a real workflow.

Prompt draft:

```text
Create a 1900x1150 image, 38:23 aspect ratio, for a section about giving an
agent the right context before it writes code. Style is clean technical editorial
with realistic monitor glow, light graphite surfaces, and restrained green/cyan
success accents. Subject: abstract implementation workspace with three empty
zones for CSS panels: a context bundle on the left, an agent plan in the center,
and a code or pull-request preparation area on the right. Around the zones,
include faint citation pins, freshness dots, source-scope boundaries, and
abstract code diff textures with no readable text. Avoid: exact GitHub or Linear
screenshots, copied Linear layout, readable code, real repository names, real
PR numbers, generic robot assistant imagery, overdone neon, and floating
dashboard cards. Intended placement: landing section 1.4 behind FIG. 1.5 build
handoff panel.
```

Final CTA visual:

- Build as CSS/product UI: CTA copy and buttons.
- Generate as bitmap: optional low-contrast continuation of the context routing
  motif. Do not make a generic marketing illustration.

Prompt draft:

```text
Create a 2200x700 wide footer background, 22:7 aspect ratio. Style is quiet
technical editorial, light graphite on near-white, sparse cyan and green
signals. Subject: a low-contrast field of abstract evidence tokens, citation
pins, and routing lines converging toward a clean central area reserved for CTA
copy and buttons rendered in CSS. Keep the image calm and spacious. Avoid:
readable text, logos, Linear page composition, customer logos, people,
decorative blobs, gradient-only backgrounds, and generic AI symbols. Intended
placement: final landing CTA background.
```

## Later App Page Asset Inventory

These pages should mostly rely on CSS product panels because users need to read,
filter, copy, inspect, and trust the UI. Generated bitmaps should appear only as
small empty-state accents, source-object thumbnails, or non-critical background
plates.

### Login

- Build as CSS/product UI: login form, workspace access note, auth provider
  buttons, and permission-aware context explanation.
- Generate as bitmap: optional quiet side or header image showing a workspace
  scope boundary.

Prompt draft:

```text
Create a 1200x900 image, 4:3 aspect ratio, for a login page side panel. Style is
minimal technical editorial on a near-white background. Subject: abstract
workspace boundary with source cards inside a soft rectangular scope, one
context bundle card entering from the edge, and small lock and freshness signals.
No readable text or logos. Avoid: office people, security shield cliches,
generic cloud dashboards, Linear screenshots, provider logos, and marketing
claims. Intended placement: optional login page supporting visual beside the CSS
login form.
```

### Context Console

- Build as CSS/product UI: query input, source filters, access mode selector,
  cited context bundle, freshness summary, permission exclusions, copy action,
  evidence links, and source links.
- Generate as bitmap: none for the primary screen. Use a tiny empty-state
  visual only when no sources are connected.

Prompt draft:

```text
Create a 900x640 empty-state illustration, 45:32 aspect ratio. Style is precise
technical editorial, light background, crisp graphite lines, restrained cyan and
amber accents. Subject: an empty context console represented by an abstract
query field outline connected to four muted source cards and one inactive
citation bundle. No readable text. Avoid: full dashboard screenshot, Linear UI,
real logos, chatbot mascot, generic AI brain, and exaggerated empty-box art.
Intended placement: Context Console empty state before sources are connected.
```

### Agent Trace

- Build as CSS/product UI: request origin, original query, retrieval steps,
  selected evidence, excluded evidence, freshness warnings, and resulting
  context bundle.
- Generate as bitmap: optional faint trace-path background for the page header.

Prompt draft:

```text
Create a 1600x520 header background, 40:13 aspect ratio. Style is thin-line
technical process diagram, near-white with graphite lines and sparse source
signal colors. Subject: an abstract trace path moving through request, retrieve,
filter, evidence, and response nodes, with no readable labels. Leave the lower
half low-detail for CSS page title and controls. Avoid: copying Linear timelines,
readable text, real logos, flowchart clip art, neon network maps, and decorative
gradients. Intended placement: Agent Trace page header behind CSS-rendered
metadata.
```

### Evidence Viewer

- Build as CSS/product UI: original question, cited chunks, coverage,
  freshness, conflict or stale signals, permission decisions, and source-object
  links.
- Generate as bitmap: small source-truth accent for no evidence pack or stale
  context state.

Prompt draft:

```text
Create a 1000x760 image, 25:19 aspect ratio, for an Evidence Viewer empty or
stale state. Style is quiet editorial technical illustration. Subject: a stack
of abstract citation cards with one timestamp marker dimmed, a small stale
indicator dot, and a linked source-object card in the background. Use muted
amber for staleness and graphite for structure. No readable text. Avoid: warning
sirens, legal scales, Linear screenshots, copied card layouts, real provider
logos, real source names, and generic analytics widgets. Intended placement:
Evidence Viewer empty or stale-context state.
```

### Source Browser

- Build as CSS/product UI: provider selector, source list, object list, object
  detail, chunks, files, metadata, relationships, and evidence links.
- Generate as bitmap: reusable neutral thumbnails for source objects when
  payload previews are unavailable.

Prompt draft:

```text
Create a 1600x1000 sprite-sheet style image, 8:5 aspect ratio, containing eight
neutral source-object thumbnail tiles in a consistent style. Style is clean
technical editorial with light paper and screen surfaces. Subjects should
include abstract chat thread, code diff, pull request review, issue checklist,
repo architecture doc, runbook page, source file tree, and evidence bundle.
Use no readable text, no logos, and no exact product UI chrome. Avoid: Linear
issue screenshots, actual Slack/GitHub/Linear visual identity, real names,
issue IDs, customer content, glossy stock icons, and generic dashboard charts.
Intended placement: Source Browser fallback thumbnails for object lists.
```

### Source Health

- Build as CSS/product UI: connected sources, selected scopes, sync status,
  freshness, cursor position, last backfill, latest error, reauth warnings, and
  stale ACL warnings.
- Generate as bitmap: optional page-header or empty-state accent showing source
  freshness, not the health matrix itself.

Prompt draft:

```text
Create a 1500x720 image, 25:12 aspect ratio, for a Source Health page accent.
Style is restrained technical editorial with light background, graphite grid,
and health signals in green, amber, and muted red. Subject: abstract sync
cursor lines moving across four source lanes, with tiny timestamp dots, backfill
blocks, and one reauthorization marker. No readable text or logos. Avoid:
server-room photos, generic uptime dashboards, Linear UI, provider brand colors,
alarm-heavy warning art, and stock analytics charts. Intended placement: Source
Health page header or empty state behind CSS health controls.
```

### Connectors

- Build as CSS/product UI: connection cards, authorization status, selected
  scopes, backfill status, reauthorization warnings, and actions.
- Generate as bitmap: small neutral connector illustrations for cards only if
  CSS icons feel too sparse.

Prompt draft:

```text
Create a 1200x800 image, 3:2 aspect ratio, for connector card illustrations.
Style is minimal technical editorial, light background, crisp graphite shapes,
restrained source-specific accent colors without copying provider brand
identity. Subject: four abstract connector modules represented by neutral plugs,
document stacks, sync arrows, scope boundaries, and small permission marks. No
readable text, no logos. Avoid: actual Slack/GitHub/Linear icons, Linear
screenshots, generic integration puzzle pieces, corporate handshake imagery,
and decorative blob backgrounds. Intended placement: optional Connectors page
card art or empty state.
```

### Developer Setup

- Build as CSS/product UI: MCP config snippet, CLI examples, UI link, copy
  button, and sample agent prompt.
- Generate as bitmap: optional background showing terminal/editor ambience with
  no readable code.

Prompt draft:

```text
Create a 1600x900 image, 16:9 aspect ratio, for a Developer Setup page
background. Style is calm technical editorial with light terminal/editor
surfaces, graphite code-line placeholders, and sparse cyan and green status
lights. Subject: a setup workspace with blank areas for CSS-rendered MCP config,
CLI command, and UI context-console link. Include abstract keyboard edge,
terminal glow, and context bundle token, but no readable code. Avoid: real shell
commands, API keys, real file paths, Linear layout, provider logos, hacker
styling, and dark cyberpunk visuals. Intended placement: Developer Setup header
or side plate behind CSS setup snippets.
```

### Later Settings And Admin

- Build as CSS/product UI: members, roles, billing portal, retention policy,
  deletion/export requests, provider principal mappings, workspace settings, and
  audit logs.
- Generate as bitmap: no primary bitmap recommended. Admin pages should feel
  utilitarian and product-native.
- Optional asset: a tiny neutral empty-state accent for lifecycle or provider
  ACL pages, using the permission-exclusion prompt from section 1.3.

### Later Optional Pages

- Canonical decisions and conflicts: build decision lists, conflict markers, and
  source citations in CSS. Optional generated bitmap: abstract forked evidence
  paths for empty state.
- Support diagnostics: build logs, checks, and status in CSS. Optional generated
  bitmap: small non-readable diagnostics trace.
- Cost and usage: build charts in CSS or chart library. Do not generate chart
  screenshots.
- Visual relationship graph: build the graph in SVG/canvas or a graph library.
  Do not generate a static bitmap for the interactive graph.
- Saved context bundles: build bundle cards and citations in CSS. Optional
  generated bitmap: source-object thumbnail variants from the Source Browser
  sprite sheet.

Prompt draft for optional canonical-conflict empty state:

```text
Create a 1000x700 image, 10:7 aspect ratio, for an empty or conflict state about
canonical decisions. Style is precise technical editorial, light background,
graphite structure, restrained amber and cyan accents. Subject: two abstract
evidence paths converging on a decision card, with one small conflict marker and
several citation pins. No readable text. Avoid: legal courtroom imagery,
Linear-like issue cards, real names, real IDs, logos, generic AI symbols, and
dramatic warning art. Intended placement: optional Canonical Decisions page
empty or conflict state.
```

## Product UI Panels To Build In CSS

Build these as live CSS/HTML components, not generated bitmaps:

- Landing `FIG. 1.1` product-system map, including real labels, connector
  lines, and evidence bundle.
- Landing `FIG. 1.2` prompt-to-agent panel, including the sample prompt and MCP,
  CLI, UI mode chips.
- Landing `FIG. 1.3` retrieval panel, including provider columns, selected
  source count, freshness, and excluded results.
- Landing `FIG. 1.4` evidence pack inspector, including citations, coverage,
  freshness, permission decisions, and links.
- Landing `FIG. 1.5` build handoff panel, including context bundle, agent plan,
  and PR/code preparation state.
- All authenticated app forms, navigation, tables, cards, filters, copied setup
  snippets, code samples, context answers, evidence chunks, source object
  metadata, health matrices, connector actions, admin controls, and charts.

Reasons:

- Text must be readable, accessible, responsive, and easy to change.
- Product panels need hover, copy, link, filter, and empty/error states.
- Generated UI screenshots can hallucinate claims, copy, logos, and layout
  details that create legal and product risk.
- CSS panels keep Cortex visually original while allowing the landing page to
  borrow a disciplined product-storytelling rhythm.

## Review Checklist For Legal And Style Safety

Before generating or shipping any asset, verify:

- The prompt does not ask for Linear screenshots, Linear wording, Linear layout,
  Linear assets, Linear issue IDs, customer quotes, or Linear-specific claims.
- The generated image does not visually recreate a Linear page section, product
  card, icon set, issue screen, navigation layout, or color treatment.
- Any numbered chapters and figure labels are rendered in CSS and are part of
  Cortex page structure, not copied from a screenshot.
- Provider names, logos, and brand marks are not generated inside bitmaps. Use
  text labels or approved icons in CSS where needed.
- No readable generated text appears in the bitmap, especially fake claims,
  fake customer data, fake source content, API keys, repository names, user
  names, issue IDs, PR numbers, or setup commands.
- Every product claim in adjacent CSS copy comes from Cortex docs and avoids
  broad unsupported claims.
- The asset shows agent-context retrieval, evidence, freshness, permissions, or
  source truth. If it could belong to any generic SaaS dashboard, revise it.
- The asset supports a product panel instead of replacing one that users need to
  read or operate.
- The visual palette is not one-note, overly purple/blue, neon, beige, or copied
  from a provider brand.
- The asset still works when cropped at desktop and mobile breakpoints, with
  enough safe space for CSS figure labels, headings, and controls.
