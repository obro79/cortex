"""Static consistency report for the fixture-only hackathon packet."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
paths = [
    ROOT / "README.md",
    ROOT / "docs/hackathon/evidence-and-provenance.md",
    ROOT / "assets/hackathon/scoreboard.svg",
]
packet = "\n".join(path.read_text().lower() for path in paths)
# Text can spell the counts out in prose; the machine-readable SVG uses numerals.
required = {
    "10 source records": ("10 source records", "10 synthetic records"),
    "Slack": ("slack",),
    "Google Drive": ("google drive",),
    "Linear": ("linear",),
    "GitHub": ("github",),
    "Jira": ("jira",),
    "repository docs": ("repository docs", "repo docs"),
    "3 media-source files": ("3 media-source files", "three media source files"),
    "2 captions": ("2 captions", "two captions"),
    "1 transcript": ("1 transcript", "one transcript"),
    "NOT LIVE": ("not live",),
}
missing = [
    label
    for label, options in required.items()
    if not any(option in packet for option in options)
]
report = ROOT / "docs/hackathon/evidence-report.md"
status = "PASS" if not missing else "FAIL"
checked_artifacts = "\n".join(f"- `{path.relative_to(ROOT)}`" for path in paths)
outcome = (
    "All required fixture counts and the NOT LIVE disclosure were found.\n"
    if not missing
    else (
        "## Missing declarations\n\n"
        + "\n".join(f"- {item}" for item in missing)
        + "\n"
    )
)
report.write_text(
    "# Hackathon evidence report\n\n"
    f"**{status}** — static declaration check. Generated from packet copy; "
    "it does not contact providers.\n\n"
    "## Checked artifacts\n\n"
    f"{checked_artifacts}\n\n"
    f"{outcome}"
)
print(f"{status}: wrote {report.relative_to(ROOT)}")
if missing:
    raise SystemExit(1)
