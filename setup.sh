#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VENV_DIR="$DIR/venv"
REQ_FILE="$DIR/requirements.txt"

echo "[*] Setting up virtual environment..."

if [ ! -f "$REQ_FILE" ]; then
    echo "[!] Error: requirements.txt not found!" >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "[+] Virtual environment created."
else
    echo "[-] Virtual environment already exists, skipping creation."
fi

PIP="$VENV_DIR/bin/pip"

echo "[*] Upgrading pip..."
"$PIP" install --upgrade pip --quiet

echo "[*] Installing dependencies..."
"$PIP" install -r "$REQ_FILE"

echo "[+] Setup complete!"
