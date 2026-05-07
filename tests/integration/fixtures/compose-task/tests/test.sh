#!/bin/bash
# Verifier: pass iff the agent wrote 'hello compose' to /logs/agent/output.txt.
set -uo pipefail

REWARD_PATH="/logs/verifier/reward.txt"
mkdir -p "$(dirname "$REWARD_PATH")"

OUTPUT_FILE="/logs/agent/output.txt"
if [ -f "$OUTPUT_FILE" ] && grep -Fq "hello compose" "$OUTPUT_FILE"; then
  echo "1" > "$REWARD_PATH"
else
  echo "0" > "$REWARD_PATH"
fi
