#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-}"

if [[ -z "${PYTHON}" ]]; then
  if [[ -x "${SCRIPT_DIR}/.client-conda-env/python.exe" ]]; then
    PYTHON="${SCRIPT_DIR}/.client-conda-env/python.exe"
  elif [[ -x "${SCRIPT_DIR}/.client-conda-env/bin/python" ]]; then
    PYTHON="${SCRIPT_DIR}/.client-conda-env/bin/python"
  else
    PYTHON="python3"
  fi
fi

exec "${PYTHON}" -m client.infra.docker.flyinnas_deploy --repo-root "${SCRIPT_DIR}" "$@"
