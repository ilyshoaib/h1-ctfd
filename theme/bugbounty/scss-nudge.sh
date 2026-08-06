#!/usr/bin/env bash
# Durable live-rebuild helper for the MountainTech theme.
#
# `vite build --watch` only watches the SCSS *entry* (main.scss) and caches its
# compiled result keyed on the entry's *content* — so edits to @use partials
# (e.g. includes/components/_cyber.scss) are invisible. This watches all source
# and, on any change, rewrites a rotating marker comment in main.scss. That
# content change busts Vite's cache and forces a full recompile that re-reads
# every partial from disk.
set -u
cd "$(dirname "$0")"
MAIN="assets/scss/main.scss"

echo "[scss-nudge] watching assets/scss and assets/js ..."
while inotifywait -qq -r -e close_write,create,delete,move \
    --exclude '(main\.scss$|\.nudge)' \
    assets/scss assets/js; do
  # strip any previous marker, then append a fresh one (nanosecond epoch)
  sed -i '/^\/\* nudge:/d' "$MAIN"
  printf '/* nudge:%s */\n' "$(date +%s%N)" >> "$MAIN"
  echo "[scss-nudge] source changed -> nudged main.scss"
done
