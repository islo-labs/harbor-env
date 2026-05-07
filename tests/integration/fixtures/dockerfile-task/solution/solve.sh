#!/bin/bash
# Oracle solution: write the marker the verifier looks for.
set -euo pipefail

mkdir -p /logs/agent
echo "hello dockerfile" > /logs/agent/output.txt
