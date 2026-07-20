#!/usr/bin/env bash
# Build and validate the deterministic-fixture Cortex hackathon teaser.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIDEO_DIR="$ROOT/deliverables/video"
OUTPUT="$VIDEO_DIR/cortex-hackathon-fixture-teaser.mp4"
CAPTIONS="$VIDEO_DIR/captions.srt"
MANIFEST="$VIDEO_DIR/artifact-manifest.json"
FONT="${CORTEX_VIDEO_FONT:-/System/Library/Fonts/Supplemental/Arial.ttf}"

for command in ffmpeg ffprobe shasum; do
  command -v "$command" >/dev/null 2>&1 || {
    printf 'Required command not found: %s\n' "$command" >&2
    exit 1
  }
done

[[ -f "$CAPTIONS" ]] || { printf 'Missing captions: %s\n' "$CAPTIONS" >&2; exit 1; }
[[ -f "$FONT" ]] || { printf 'Missing font: %s (set CORTEX_VIDEO_FONT)\n' "$FONT" >&2; exit 1; }

if ! rg -q 'session_accessed: false' "$CAPTIONS" || ! rg -q 'no native Claude session resume or fork' "$CAPTIONS"; then
  printf 'Caption safety disclosure is incomplete.\n' >&2
  exit 1
fi

TEMP_OUTPUT="$(mktemp "${TMPDIR:-/tmp}/cortex-hackathon-video.XXXXXX.mp4")"
trap 'rm -f "$TEMP_OUTPUT"' EXIT

ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i 'color=c=0x08111f:s=1280x720:r=30:d=72' \
  -vf "drawbox=x=0:y=0:w=iw:h=70:color=0x0e7490@0.95:t=fill,drawbox=x=0:y=680:w=iw:h=40:color=0x111827@0.96:t=fill,drawtext=fontfile=${FONT}:text='CORTEX  |  DETERMINISTIC FIXTURE DEMO  |  NO LIVE PROVIDERS':x=42:y=22:fontsize=23:fontcolor=white,drawtext=fontfile=${FONT}:text='Local, reproducible fixture workflow':x=42:y=691:fontsize=17:fontcolor=0xd1d5db,subtitles=${CAPTIONS}:force_style='FontName=Arial,FontSize=30,PrimaryColour=&H00F9FAFB,OutlineColour=&H00111827,BorderStyle=1,Outline=2,Shadow=0,Alignment=5,MarginV=82'" \
  -c:v libx264 -profile:v high -level 4.0 -pix_fmt yuv420p -movflags +faststart \
  "$TEMP_OUTPUT"

mv "$TEMP_OUTPUT" "$OUTPUT"
trap - EXIT

DURATION="$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT")"
VIDEO_STREAM="$(ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -of csv=p=0 "$OUTPUT")"
AUDIO_STREAMS="$(ffprobe -v error -select_streams a -show_entries stream=index -of csv=p=0 "$OUTPUT")"

awk -v duration="$DURATION" 'BEGIN { exit !(duration >= 71.9 && duration <= 72.1) }' || {
  printf 'Unexpected duration: %s\n' "$DURATION" >&2
  exit 1
}
[[ "$VIDEO_STREAM" == "h264,1280,720" ]] || { printf 'Unexpected video stream: %s\n' "$VIDEO_STREAM" >&2; exit 1; }
[[ -z "$AUDIO_STREAMS" ]] || { printf 'Unexpected audio streams: %s\n' "$AUDIO_STREAMS" >&2; exit 1; }

SHA256="$(shasum -a 256 "$OUTPUT" | awk '{print $1}')"
printf '{\n  "artifact": "cortex-hackathon-fixture-teaser.mp4",\n  "classification": "deterministic-fixture-demo",\n  "duration_seconds": 72,\n  "video": "h264 1280x720",\n  "audio": "none",\n  "live_providers": false,\n  "session_accessed": false,\n  "native_claude_session_resume_or_fork": false,\n  "sha256": "%s"\n}\n' "$SHA256" > "$MANIFEST"

printf 'Built and validated %s\n' "$OUTPUT"
