#!/usr/bin/env bash
# lore test suite: syntax gate + stdlib unittest. No third-party deps.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== py_compile =="
python3 -m py_compile lore
echo "OK"
echo
echo "== unittest =="
cd tests
python3 -m unittest discover -s . -p 'test_*.py' -v
