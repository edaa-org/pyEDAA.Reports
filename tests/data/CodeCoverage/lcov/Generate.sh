#!/usr/bin/env bash
# Generates the lcov tracefiles of the fixtures with the real tools, each in a temporary copy of its sources:
#   C/GCC.info          gcc --coverage + lcov --capture (lcov 2.3, GCC 14)
#   C/LLVM.info         clang + llvm-cov export -format=lcov (LLVM 19)
#   VHDL/GHDL.info      ghdl --coverage + ghdl coverage --format=lcov (GHDL 7.0-dev, mcode backend)
#   ../Python/coverage.info  coverage run + coverage lcov (coverage.py 7.16)
set -o pipefail

Fixtures="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
Work="$(mktemp -d)" || { printf -- 'Cannot create a temporary directory.\n' >&2; exit 1; }
trap 'rm -rf -- "${Work}"' EXIT

Fail() {
	printf -- '%s\n' "$1" >&2
	exit 1
}

# GCC + lcov: branches, MC/DC conditions, function end lines, line checksums; the source paths made relative.
mkdir -p "${Work}/gcc" && cp "${Fixtures}/C/"{Classify.c,Clamp.h} "${Work}/gcc/" || Fail "Cannot copy the C sources."
(
	cd "${Work}/gcc" || exit 1
	gcc --coverage -fcondition-coverage -O0 -o Classify Classify.c && ./Classify > /dev/null &&
	lcov --capture --directory . --branch-coverage --mcdc-coverage --checksum --test-name Classify \
		--substitute "s#^${Work}/gcc/##" --output-file "${Fixtures}/C/GCC.info" > /dev/null
) || Fail "Cannot generate 'C/GCC.info'."

# clang + llvm-cov: source paths relative to the compilation directory.
mkdir -p "${Work}/llvm" && cp "${Fixtures}/C/"{Classify.c,Clamp.h} "${Work}/llvm/" || Fail "Cannot copy the C sources."
(
	cd "${Work}/llvm" || exit 1
	clang -fprofile-instr-generate -fcoverage-mapping -fcoverage-compilation-dir=. -O0 -o Classify Classify.c &&
	LLVM_PROFILE_FILE=Classify.profraw ./Classify > /dev/null &&
	llvm-profdata merge -sparse -o Classify.profdata Classify.profraw &&
	llvm-cov export -format=lcov -instr-profile=Classify.profdata Classify > "${Fixtures}/C/LLVM.info"
) || Fail "Cannot generate 'C/LLVM.info'."

# GHDL: 'ghdl coverage' writes the tracefile to stdout.
mkdir -p "${Work}/ghdl" && cp "${Fixtures}/VHDL/"{Classify,Testbench}.vhdl "${Work}/ghdl/" ||
	Fail "Cannot copy the VHDL sources."
(
	cd "${Work}/ghdl" || exit 1
	ghdl -a --coverage Classify.vhdl Testbench.vhdl && ghdl --elab-run --coverage Testbench > /dev/null &&
	ghdl coverage --format=lcov coverage-*.json > "${Fixtures}/VHDL/GHDL.info"
) || Fail "Cannot generate 'VHDL/GHDL.info'."

# coverage.py: the Python fixture package, exercised by 'Run.py', configured by '.coveragerc'.
cp -r "${Fixtures}/../Python" "${Work}/python" || Fail "Cannot copy the Python fixture."
(
	cd "${Work}/python" || exit 1
	coverage run Run.py && coverage lcov -o "${Fixtures}/../Python/coverage.info" > /dev/null
) || Fail "Cannot generate '../Python/coverage.info'."
