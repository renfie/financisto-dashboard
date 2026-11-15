#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $(id -u) -eq 0 ]]; then
  echo 'Bitte als normaler Projektbenutzer ohne sudo installieren.' >&2
  exit 1
fi
if [[ $# -eq 0 ]]; then
  exec python3 src/setup_secrets.py --install
elif [[ $# -eq 1 && $1 == '--verify' ]]; then
  exec python3 src/setup_secrets.py --verify
elif [[ $# -eq 1 && $1 == '--resume' ]]; then
  exec python3 src/setup_secrets.py --resume
else
  echo 'Verwendung: ./install.sh [--verify|--resume]'
  exit 2
fi
