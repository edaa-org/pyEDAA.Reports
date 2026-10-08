#!/usr/bin/env bash
# Generates the lcov tracefiles of the fixtures with the real tools, each in a temporary copy of its sources:
#   VHDL/GHDL.info      ghdl --coverage + ghdl coverage --format=lcov (GHDL 7.0-dev, mcode backend)
set -o pipefail

Fixtures="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
Work="$(mktemp -d)" || { printf -- 'Cannot create a temporary directory.\n' >&2; exit 1; }
trap 'rm -rf -- "${Work}"' EXIT

Fail() {
	printf -- '%s\n' "$1" >&2
	exit 1
}

# GHDL: 'ghdl coverage' writes the tracefile to stdout.
mkdir -p "${Work}/ghdl" && cp "${Fixtures}/VHDL/"{Classify,Testbench}.vhdl "${Work}/ghdl/" ||
	Fail "Cannot copy the VHDL sources."
(
	cd "${Work}/ghdl" || exit 1
	ghdl -a --coverage Classify.vhdl Testbench.vhdl && ghdl --elab-run --coverage Testbench > /dev/null &&
	ghdl coverage --format=lcov coverage-*.json > "${Fixtures}/VHDL/GHDL.info"
) || Fail "Cannot generate 'VHDL/GHDL.info'."
