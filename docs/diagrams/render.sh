#!/usr/bin/env bash
# Render every docs/diagrams/*.mmd to .svg with a pinned mermaid-cli image; print each exit code and the source sha256.
set -u
IMG=minlag/mermaid-cli:11.4.2
cd "$(dirname "$0")"
rc=0
for f in *.mmd; do
  docker run --rm -u "$(id -u):$(id -g)" -v "$PWD":/data "$IMG" -c /data/mermaid.json -i "/data/$f" -o "/data/${f%.mmd}.svg" >/dev/null 2>&1
  e=$?; [ $e -ne 0 ] && rc=1
  echo "$f exit=$e sha256=$(shasum -a 256 "$f" | cut -d' ' -f1)"
done
exit $rc
