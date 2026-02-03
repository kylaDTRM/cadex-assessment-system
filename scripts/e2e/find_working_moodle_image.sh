#!/usr/bin/env bash
set -euo pipefail

# Probe candidate Moodle image tags and print the first that can be pulled.
# Usage: ./scripts/e2e/find_working_moodle_image.sh

CANDIDATES=(
  "bitnami/moodle:4"
  "bitnami/moodle:4.1"
  "bitnami/moodle:4.0"
  "bitnami/moodle:3"
  "bitnami/moodle:latest"
  "moodlehq/moodle-php-apache:4.1"
  "moodlehq/moodle-php-apache:4.0"
  "linuxserver/moodle:latest"
)

for img in "${CANDIDATES[@]}"; do
  echo "Trying docker pull $img" >&2
  if docker pull "$img" >/dev/null 2>&1; then
    echo "$img"
    exit 0
  else
    echo "Pull failed: $img" >&2
  fi
done

echo "No candidate Moodle images could be pulled." >&2
exit 1
