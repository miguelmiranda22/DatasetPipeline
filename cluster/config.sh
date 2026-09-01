#!/bin/bash
BASE_DIR="${BASE_DIR:-$HOME/paas_rerun}"
WORK_DIR="$BASE_DIR/run"
PIPE_DIR="${PIPE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CHEMBL_DB="${CHEMBL_DB:-$HOME/chembl_37/chembl_37_sqlite/chembl_37.db}"
REF_DIR="${REF_DIR:-$HOME/Classification}"
PARTITION="${PARTITION:-compute}"
PRUNING_SIZE="${PRUNING_SIZE:-5000}"
LOG_DIR="$WORK_DIR/logs"
export BASE_DIR WORK_DIR PIPE_DIR CHEMBL_DB REF_DIR PARTITION LOG_DIR PRUNING_SIZE
