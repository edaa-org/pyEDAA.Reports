#!/usr/bin/env bash
# Generate the llvm-cov export reports of the C and C++ sources in 'src/' and 'include/'.
#
# The program is compiled with clang's source-based code coverage - and MC/DC coverage -, run once, and its profile is
# exported by each given llvm-cov to 'coverage-<format version>.json'. The sources are mapped to '/project'.
#
# Usage: ./Generate.sh [llvm-cov ...]       Default: llvm-cov

set -o pipefail

directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# -eq 0 ]]; then
	set -- llvm-cov
fi

build="$(mktemp -d)"
if [[ $? -ne 0 || ! -d "${build}" ]]; then
	printf -- 'ERROR: Cannot create a temporary build directory.\n' 1>&2
	exit 1
fi
trap 'rm -rf "${build}"' EXIT

flags=(-fprofile-instr-generate -fcoverage-mapping -fcoverage-mcdc -fcoverage-compilation-dir=/project -Iinclude)

cd "${directory}" || exit 1
if ! clang "${flags[@]}" -c src/Statistics.c -o "${build}/Statistics.o"; then
	printf -- 'ERROR: Cannot compile src/Statistics.c.\n' 1>&2
	exit 1
elif ! clang++ "${flags[@]}" -c src/Shapes.cpp -o "${build}/Shapes.o"; then
	printf -- 'ERROR: Cannot compile src/Shapes.cpp.\n' 1>&2
	exit 1
elif ! clang++ -fprofile-instr-generate "${build}/Statistics.o" "${build}/Shapes.o" -o "${build}/Program"; then
	printf -- 'ERROR: Cannot link the program.\n' 1>&2
	exit 1
elif ! LLVM_PROFILE_FILE="${build}/Program.profraw" "${build}/Program"; then
	printf -- 'ERROR: The program failed.\n' 1>&2
	exit 1
elif ! llvm-profdata merge -sparse "${build}/Program.profraw" -o "${build}/Program.profdata"; then
	printf -- 'ERROR: Cannot merge the raw profile.\n' 1>&2
	exit 1
fi

for llvmCov in "$@"; do
	if ! "${llvmCov}" export -format=text -instr-profile="${build}/Program.profdata" "${build}/Program" \
			> "${build}/coverage.json"; then
		printf -- 'ERROR: %s can not export the coverage.\n' "${llvmCov}" 1>&2
		exit 1
	fi

	version="$(grep -o '"version":"[0-9.]*"' "${build}/coverage.json" | cut -d '"' -f 4)"
	if [[ -z "${version}" ]]; then
		printf -- 'ERROR: The report of %s states no format version.\n' "${llvmCov}" 1>&2
		exit 1
	fi

	mv "${build}/coverage.json" "${directory}/coverage-${version}.json"
	printf -- 'coverage-%s.json written by %s.\n' "${version}" "${llvmCov}"
done
