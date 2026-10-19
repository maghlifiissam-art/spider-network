#!/bin/sh
# Compress a RIMAZ reel poster before upload/publish. Usage: compress_poster.sh in.jpg out.jpg
# Budget: max 400px wide, JPEG q~7 (typically 15-26KB). Fail if output > 40KB.
set -e
ffmpeg -v error -y -i "$1" -vf "scale='min(400,iw)':-2" -q:v 7 -pix_fmt yuvj420p "$2"
[ "$(stat -c%s "$2")" -le 40000 ] || { echo "poster over 40KB budget" >&2; exit 1; }
