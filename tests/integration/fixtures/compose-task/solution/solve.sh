#!/bin/bash
# Oracle solution: write the marker the verifier looks for.
set -euo pipefail

mkdir -p /logs/agent
echo "hello compose" > /logs/agent/output.txt
