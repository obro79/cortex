# Demo run of show — 4 minutes

## Setup (before judges arrive)

Open the local demo/workbench and the evidence panel. Keep the scoreboard and
architecture context available in separate tabs. Say up front: “This is a
deterministic synthetic-fixture demo; it is not connected to live providers.”

## Script

| Time | Operator action | Narration |
| --- | --- | --- |
| 0:00–0:30 | Show the scoreboard. | “Cortex’s walkthrough has 10 synthetic records across the source shapes teams actually use; three are media files with accessibility derivatives.” |
| 0:30–1:05 | Show architecture context. | “Cortex is MCP-first with a companion control plane. The durable direction keeps Postgres canonical and intends hosted Qdrant for the derived vector index; neither is claimed as deployed by this demo.” |
| 1:05–2:10 | Ask the prepared cross-source question in the workbench. | “Instead of hunting through messages and tickets, I ask for the decision and its rationale.” |
| 2:10–3:00 | Open the answer’s evidence rows. | “The answer is useful only if it is inspectable: source, fixture ID, excerpt, and route back to context.” |
| 3:00–3:25 | Open a media-derived caption/transcript item. | “Media is represented with derived text so it can participate in the same evidence trail.” |
| 3:25–3:50 | Call `create_handoff_bundle` over local MCP. | “This creates an opt-in portable handoff with evidence references. It reports `session_accessed: false`; it does not resume or fork a Claude session.” |
| 3:50–4:00 | Return to scoreboard and disclosure. | “The demo proves the flow on fixtures. Live connectors and production validation remain separate work.” |

## Recovery path

If the interactive surface is unavailable, use the architecture context,
scoreboard, and prepared evidence screenshots/fixtures to narrate the same
source → evidence → answer flow. Do not substitute a claim that a live provider
was queried.

## Operator checklist

- Verify the visible **NOT LIVE / synthetic fixtures** disclosure.
- Never expose credentials, tokens, or non-fixture data.
- Use the stated counts exactly; do not count caption/transcript derivatives as
  additional source records.
