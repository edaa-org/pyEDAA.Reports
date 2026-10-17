#!/usr/bin/env bash
# Generate the gcov JSON reports of the C and C++ sources in this directory with GCC 14.
#
# * 'Main.gcov.json.gz': gzip-compressed JSON of 'Main.cpp', as gcov writes it by default.
# * 'All.gcov.json':     plain JSON of 'Statistics.c' and 'Main.cpp', one line per data file, as gcov writes it to
#                        the standard output.
#
# The sources are built in a temporary directory, which gcov reports as 'current_working_directory'.

Directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WorkDirectory="$(mktemp -d)"
if [[ $? -ne 0 || ! -d "${WorkDirectory}" ]]; then
	printf -- 'ERROR: Cannot create a temporary directory.\n' >&2
	exit 1
fi
trap 'rm -rf "${WorkDirectory}"' EXIT

cp -r "${Directory}/Statistics.c" "${Directory}/Main.cpp" "${Directory}/Containers" "${WorkDirectory}/" || {
	printf -- 'ERROR: Cannot copy the sources to "%s".\n' "${WorkDirectory}" >&2
	exit 1
}
cd "${WorkDirectory}" || exit 1

CompilerOptions=(--coverage -fcondition-coverage -O0)
gcc "${CompilerOptions[@]}" -c Statistics.c -o Statistics.o && gcc --coverage -o statistics Statistics.o || {
	printf -- 'ERROR: Cannot build "Statistics.c".\n' >&2
	exit 1
}
g++ "${CompilerOptions[@]}" -c Main.cpp -o Main.o && g++ --coverage -o stack Main.o || {
	printf -- 'ERROR: Cannot build "Main.cpp".\n' >&2
	exit 1
}
./statistics && ./stack || {
	printf -- 'ERROR: A program failed.\n' >&2
	exit 1
}

# --relative-only leaves out the system headers' inline functions.
GCovOptions=(--json-format --branch-probabilities --conditions --relative-only)
gcov "${GCovOptions[@]}" Main.cpp > /dev/null || {
	printf -- 'ERROR: gcov failed on "Main.cpp".\n' >&2
	exit 1
}
gcov "${GCovOptions[@]}" --stdout Statistics.c Main.cpp > All.gcov.json || {
	printf -- 'ERROR: gcov failed on "Statistics.c" and "Main.cpp".\n' >&2
	exit 1
}

cp Main.gcov.json.gz All.gcov.json "${Directory}/" || {
	printf -- 'ERROR: Cannot copy the reports to "%s".\n' "${Directory}" >&2
	exit 1
}
printf -- 'Reports written to "%s".\n' "${Directory}"
