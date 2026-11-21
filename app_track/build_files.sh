#!/bin/bash
set -e

echo "=== Installing Python dependencies ==="
python3 -m pip install -r requirements.txt

echo "=== Collecting Django static files ==="
python3 manage.py collectstatic --no-input --clear

echo "=== Build completed successfully ==="
