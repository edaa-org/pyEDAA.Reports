#!/usr/bin/env bash
# Generate the JaCoCo XML reports of the Java sources in this directory with JaCoCo 0.8.15 and a JDK.
#
# * 'jacoco.xml':        the report of JaCoCo's CLI: packages below the report.
# * 'jacoco-groups.xml': the report of 'GroupedReport.java', written with the API of JaCoCo's CLI JAR: nested groups
#                        of packages, as Maven's goal 'report-aggregate' or Ant's task 'report' write them.
#
# 'util/Numbers.java' is compiled without debug information, so its class names no source file and its methods no line.
#
# Usage: Generate.sh <directory>
#   <directory> holds 'org.jacoco.cli-0.8.15-nodeps.jar' and 'org.jacoco.agent-0.8.15-runtime.jar' from Maven Central.

JaCoCoVersion="0.8.15"

if [[ $# -ne 1 ]]; then
	printf -- 'ERROR: Expected one argument, the directory of the JaCoCo JARs.\n' >&2
	printf -- 'Usage: %s <directory>\n' "${0}" >&2
	exit 1
fi
CLIJar="$(realpath "${1}/org.jacoco.cli-${JaCoCoVersion}-nodeps.jar")"
AgentJar="$(realpath "${1}/org.jacoco.agent-${JaCoCoVersion}-runtime.jar")"
for Jar in "${CLIJar}" "${AgentJar}"; do
	if [[ ! -f "${Jar}" ]]; then
		printf -- 'ERROR: JAR file "%s" not found.\n' "${Jar}" >&2
		exit 1
	fi
done

Directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WorkDirectory="$(mktemp -d)"
if [[ $? -ne 0 || ! -d "${WorkDirectory}" ]]; then
	printf -- 'ERROR: Cannot create a temporary directory.\n' >&2
	exit 1
fi
trap 'rm -rf "${WorkDirectory}"' EXIT
cd "${WorkDirectory}" || exit 1

javac -d classes -g:none "${Directory}/src/util/Numbers.java" || {
	printf -- 'ERROR: Cannot compile "util/Numbers.java".\n' >&2
	exit 1
}
javac -d classes -cp classes "${Directory}/src/Main.java" "${Directory}/src/shapes/"*.java || {
	printf -- 'ERROR: Cannot compile "Main.java" and package "shapes".\n' >&2
	exit 1
}
javac -d generator -cp "${CLIJar}" "${Directory}/GroupedReport.java" || {
	printf -- 'ERROR: Cannot compile "GroupedReport.java".\n' >&2
	exit 1
}
java "-javaagent:${AgentJar}=destfile=jacoco.exec" -cp classes Main > /dev/null || {
	printf -- 'ERROR: The program failed.\n' >&2
	exit 1
}

java -jar "${CLIJar}" report jacoco.exec --classfiles classes --sourcefiles "${Directory}/src" --name JaCoCo-CLI \
	--xml jacoco.xml --quiet || {
	printf -- 'ERROR: JaCoCo CLI failed.\n' >&2
	exit 1
}
java -cp "generator:${CLIJar}" GroupedReport jacoco.exec classes "${Directory}/src" jacoco-groups.xml || {
	printf -- 'ERROR: "GroupedReport" failed.\n' >&2
	exit 1
}

cp jacoco.xml jacoco-groups.xml "${Directory}/" || {
	printf -- 'ERROR: Cannot copy the reports to "%s".\n' "${Directory}" >&2
	exit 1
}
printf -- 'Reports written to "%s".\n' "${Directory}"
