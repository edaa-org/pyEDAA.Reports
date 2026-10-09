#! /usr/bin/env bash
# Simulates the testbench 'Counter_tb' twice with NVC's statement and branch coverage - counting, then counting with
# resets -, merges both coverage databases and exports them as Cobertura XML ('cobertura.xml'), the only export format
# of NVC. Needs NVC on PATH.

# Simulate <name> [<generic>...]
#   Writes the coverage database '<name>.ncdb'.
Simulate() {
	local name="${1}"
	if [[ -z "${name}" ]]; then
		printf -- 'Simulate: missing parameter <name>.\n' >&2
		return 1
	fi
	shift

	nvc --std=2008 --work="${workDirectory}/work" \
		-e --cover=statement,branch --cover-file="${name}.ncdb" "$@" Counter_tb -r
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
trap 'rm -r "${workDirectory}" Count.ncdb Reset.ncdb Merged.ncdb' EXIT

nvc --std=2008 --work="${workDirectory}/work" -a src/Utilities/Functions.vhdl src/Counter.vhdl tb/Counter_tb.vhdl
if [[ $? -ne 0 ]]; then
	printf -- 'Analysis of the VHDL sources failed.\n' >&2
	exit 1
fi

Simulate Count -gCYCLES=20               || exit 1
Simulate Reset -gCYCLES=3 -gRESETS=true  || exit 1

nvc --work="${workDirectory}/work" --cover-merge --output=Merged.ncdb Count.ncdb Reset.ncdb
if [[ $? -ne 0 ]]; then
	printf -- 'Merging the coverage databases failed.\n' >&2
	exit 1
fi

nvc --work="${workDirectory}/work" --cover-export --format=cobertura --output=cobertura.xml --relative=. Merged.ncdb
if [[ $? -ne 0 ]]; then
	printf -- 'Export of the coverage database to Cobertura XML failed.\n' >&2
	exit 1
fi
