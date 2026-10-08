#! /usr/bin/env bash
# Generates the NVC coverage fixtures: simulates the testbench 'Counter_tb' with each kind of coverage NVC collects,
# merges two runs, and exports each coverage database as Cobertura XML with 'nvc --cover-export'. Needs NVC on PATH.

# Simulate <name> <coverage kinds> [<generic>...]
#   Writes the coverage database '<name>.ncdb' into the temporary work directory.
Simulate() {
	local name="${1}"
	local kinds="${2}"
	if [[ -z "${name}" ]]; then
		printf -- 'Simulate: missing parameter <name>.\n' >&2
		return 1
	elif [[ -z "${kinds}" ]]; then
		printf -- 'Simulate: missing parameter <coverage kinds>.\n' >&2
		return 1
	fi
	shift 2

	nvc --work="work:${workDirectory}/work" -e --cover="${kinds}" --cover-file="${workDirectory}/${name}.ncdb" "$@" \
		Counter_tb -r
	if [[ $? -ne 0 ]]; then
		printf -- 'Simulation run '\''%s'\'' with coverage '\''%s'\'' failed.\n' "${name}" "${kinds}" >&2
		return 1
	fi
}

# Export <name>
#   Exports the coverage database '<name>.ncdb' to '<name>.xml', file names relative to the fixture directory.
Export() {
	local name="${1}"
	if [[ -z "${name}" ]]; then
		printf -- 'Export: missing parameter <name>.\n' >&2
		return 1
	fi

	nvc --work="work:${workDirectory}/work" --cover-export --format=cobertura --relative=. --output="${name}.xml" \
		"${workDirectory}/${name}.ncdb"
	if [[ $? -ne 0 ]]; then
		printf -- 'Export of coverage database '\''%s'\'' failed.\n' "${name}" >&2
		return 1
	fi
}

cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $? -ne 0 ]]; then
	printf -- 'Cannot change to the fixture directory.\n' >&2
	exit 1
fi

workDirectory="$(mktemp -d)"
if [[ $? -ne 0 ]]; then
	printf -- 'Cannot create a temporary work directory.\n' >&2
	exit 1
fi
trap 'rm -r "${workDirectory}"' EXIT

nvc --work="work:${workDirectory}/work" -a --psl src/Utilities.vhdl src/Counter.vhdl tb/Counter_tb.vhdl
if [[ $? -ne 0 ]]; then
	printf -- 'Analysis of the VHDL sources failed.\n' >&2
	exit 1
fi

# Statement and branch coverage: two runs, and both merged.
Simulate Count statement,branch -gCYCLES=20               || exit 1
Simulate Reset statement,branch -gCYCLES=8 -gRESETS=true  || exit 1

nvc --work="work:${workDirectory}/work" --cover-merge --output="${workDirectory}/Merged.ncdb" \
	"${workDirectory}/Count.ncdb" "${workDirectory}/Reset.ncdb"
if [[ $? -ne 0 ]]; then
	printf -- 'Merging the coverage databases failed.\n' >&2
	exit 1
fi

# Each other kind of coverage alone.
Simulate Branch     branch     -gCYCLES=20  || exit 1
Simulate Expression expression -gCYCLES=20  || exit 1
Simulate Toggle     toggle     -gCYCLES=20  || exit 1
Simulate FSMState   fsm-state  -gCYCLES=20  || exit 1
Simulate Functional functional -gCYCLES=20  || exit 1

for name in Count Reset Merged Branch Expression Toggle FSMState Functional; do
	Export "${name}" || exit 1
done
