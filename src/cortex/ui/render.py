from __future__ import annotations

from html import escape

from cortex.ui.auth import UiActorContext


def render_shell(*, context: UiActorContext, title: str, body: str) -> str:
    nav = "".join(
        [
            '<a href="/ui">Overview</a>',
            '<a href="/ui/sources">Sources</a>',
            '<a href="/ui/connectors">Connectors</a>',
            '<a href="/ui/jobs">Jobs</a>',
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} - Cortex</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --border: #d9dee7;
      --ink: #1f2933;
      --muted: #596575;
      --panel: #ffffff;
      --accent: #1d6f5f;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 system-ui, -apple-system, BlinkMacSystemFont,
        "Segoe UI", sans-serif;
    }}
    header {{
      border-bottom: 1px solid var(--border);
      background: var(--panel);
    }}
    .bar, main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 16px 20px;
    }}
    .bar {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
    }}
    nav a {{
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }}
    h1 {{
      margin: 0;
      font-size: 20px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 8px;
      font-size: 16px;
      letter-spacing: 0;
    }}
    .meta {{
      color: var(--muted);
      font-size: 12px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      font-weight: 600;
      color: #31566a;
      background: #eef8f6;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 760px;
    }}
    th, td {{
      border-bottom: 1px solid var(--border);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
    }}
    @media (max-width: 640px) {{
      .bar {{
        align-items: flex-start;
        flex-direction: column;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="bar">
      <div>
        <h1>Cortex</h1>
        <div class="meta">
          Workspace {escape(context.workspace_id)}
          · Actor {escape(context.actor_id)}
        </div>
      </div>
      <nav>{nav}</nav>
    </div>
  </header>
  <main>{body}</main>
</body>
</html>"""
