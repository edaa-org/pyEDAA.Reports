#! /usr/bin/env bash
# Simulates the testbench 'Counter_tb' twice with GHDL's statement coverage - counting, then counting with resets - and
# writes GHDL's coverage file of each run ('coverage-<run>.json') and an lcov tracefile of both runs ('coverage.info').
# Needs GHDL's mcode backend on PATH.

# Simulate <name> [<generic>...]
#   Writes 'coverage-<name>.json'.
Simulate() {
	local name="${1}"
	if [[ -z "${name}" ]]; then
		printf -- 'Simulate: missing parameter <name>.\n' >&2
		return 1
	fi
	shift

	ghdl -r --std=08 --workdir="${workDirectory}" --coverage --coverage-output="coverage-${name}.json" Counter_tb "$@"
	if [[ $? -ne 0 ]]; then
		printf -- 'Simulation run '\''%s'\'' failed.\n' "${name}" >&2
		return 1
	fi
}

cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $? -ne 0 ]]; then
	printf -- 'Cannot change to the example directory.\n' >&2
	exit 1
fi

workDirectory="$(mktemp -d)"
if [[ $? -ne 0 ]]; then
	printf -- 'Cannot create a temporary work directory.\n' >&2
	exit 1
fi
trap 'rm -r "${workDirectory}"' EXIT

ghdl -a --std=08 --workdir="${workDirectory}" src/Utilities/Functions.vhdl src/Counter.vhdl tb/Counter_tb.vhdl
if [[ $? -ne 0 ]]; then
	printf -- 'Analysis of the VHDL sources failed.\n' >&2
	exit 1
fi

Simulate Count -gCYCLES=20               || exit 1
Simulate Reset -gCYCLES=3 -gRESETS=true  || exit 1

ghdl coverage --format=lcov coverage-Count.json coverage-Reset.json > coverage.info
if [[ $? -ne 0 ]]; then
	printf -- 'Conversion of the coverage files to lcov failed.\n' >&2
	exit 1
fi
