#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [ "$#" -ne 1 ]; then
    echo 'Usage: ./install.sh /absolute/private/homebrain/work-directory'
    exit 2
fi
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --disable-pip-version-check -r requirements.lock
.venv/bin/python scripts/install.py --work "$1"
exec .venv/bin/python -m pytest -q
