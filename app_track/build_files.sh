#!/bin/bash
set -e

# Prevent PEP 668 externally-managed-environment errors on modern Vercel / uv
export UV_BREAK_SYSTEM_PACKAGES=1
export PIP_BREAK_SYSTEM_PACKAGES=1

echo "=== Installing Python dependencies ==="
if command -v uv &> /dev/null; then
    echo "Using uv..."
    uv pip install --system --break-system-packages -r requirements.txt || python3 -m pip install --break-system-packages -r requirements.txt
else
    echo "Using pip..."
    python3 -m pip install --break-system-packages -r requirements.txt
fi

echo "=== Collecting Django static files ==="
python3 manage.py collectstatic --no-input --clear

echo "=== Build completed successfully ==="
