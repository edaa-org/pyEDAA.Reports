<p align="center">
  <a title="edaa-org.github.io/pyEDAA.Reports" href="https://edaa-org.github.io/pyEDAA.Reports"><img height="80px" src="doc/_static/logo.svg"/></a>
</p>

[![Sourcecode on GitHub](https://img.shields.io/badge/pyEDAA-Reports-29b6f6.svg?longCache=true&style=flat-square&logo=GitHub&labelColor=0277bd)](https://GitHub.com/edaa-org/pyEDAA.Reports)
[![Documentation](https://img.shields.io/website?longCache=true&style=flat-square&label=edaa-org.github.io%2FpyEDAA.Reports&logo=GitHub&logoColor=fff&up_color=blueviolet&up_message=Read%20now%20%E2%9E%9A&url=https%3A%2F%2Fedaa-org.github.io%2FpyEDAA.Reports%2Findex.html)](https://edaa-org.github.io/pyEDAA.Reports/)
[![Gitter](https://img.shields.io/badge/chat-on%20gitter-4db797.svg?longCache=true&style=flat-square&logo=gitter&logoColor=e8ecef)](https://gitter.im/hdl/community)  
[![GitHub Workflow - Build and Test Status](https://img.shields.io/github/actions/workflow/status/edaa-org/pyEDAA.Reports/Pipeline.yml?longCache=true&style=flat-square&label=Build%20and%20Test&logo=GitHub%20Actions&logoColor=FFFFFF)](https://GitHub.com/edaa-org/pyEDAA.Reports/actions/workflows/Pipeline.yml)
[![Codacy - Quality](https://img.shields.io/codacy/grade/f8142b422c1742bdba38e8ac1893870c?longCache=true&style=flat-square&logo=Codacy)](https://app.codacy.com/gh/edaa-org/pyEDAA.Reports)

<!--
[![Sourcecode License](https://img.shields.io/pypi/l/pyEDAA.Reports?longCache=true&style=flat-square&logo=Apache&label=code)](LICENSE.md)
[![Documentation License](https://img.shields.io/badge/doc-CC--BY%204.0-green?longCache=true&style=flat-square&logo=CreativeCommons&logoColor=fff)](LICENSE.md)

[![PyPI](https://img.shields.io/pypi/v/pyEDAA.Reports?longCache=true&style=flat-square&logo=PyPI&logoColor=FBE072)](https://pypi.org/project/pyEDAA.Reports/)
![PyPI - Status](https://img.shields.io/pypi/status/pyEDAA.Reports?longCache=true&style=flat-square&logo=PyPI&logoColor=FBE072)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyEDAA.Reports?longCache=true&style=flat-square&logo=PyPI&logoColor=FBE072)

[![Libraries.io status for latest release](https://img.shields.io/librariesio/release/pypi/pyEDAA.Reports?longCache=true&style=flat-square&logo=Libraries.io&logoColor=fff)](https://libraries.io/github/edaa-org/pyEDAA.Reports)
[![Codacy - Coverage](https://img.shields.io/codacy/coverage/f8142b422c1742bdba38e8ac1893870c?longCache=true&style=flat-square&logo=Codacy)](https://app.codacy.com/gh/edaa-org/pyEDAA.Reports)
[![Codecov - Branch Coverage](https://img.shields.io/codecov/c/github/edaa-org/pyEDAA.Reports?longCache=true&style=flat-square&logo=Codecov)](https://codecov.io/gh/edaa-org/pyEDAA.Reports)

[![Dependent repos (via libraries.io)](https://img.shields.io/librariesio/dependent-repos/pypi/pyEDAA.Reports?longCache=true&style=flat-square&logo=GitHub)](https://GitHub.com/edaa-org/pyEDAA.Reports/network/dependents)
[![Requires.io](https://img.shields.io/requires/github/edaa-org/pyEDAA.Reports?longCache=true&style=flat-square)](https://requires.io/github/EDAA-ORG/pyEDAA.Reports/requirements/?branch=main)
[![Libraries.io SourceRank](https://img.shields.io/librariesio/sourcerank/pypi/pyEDAA.Reports?longCache=true&style=flat-square)](https://libraries.io/github/edaa-org/pyEDAA.Reports/sourcerank)
-->

Proposal to define an abstract model for outputs from EDA tools and logging libraries.

The main intended use case of pyEDAA.Reports is to import multiple log/report formats (raw logs, CSVs, YAML, JSON, etc.)
and provide a unified model that can generate reports using popular formats such as XUnit or Cobertura.
Since most vendors, CI services and monitoring tools support XML, the internals of pyEDAA.Reports are to be based on
XML transformations.

As an abstract model, the main capability of pyEDAA.Reports is handling messages using an structured format.
The readers categorize messages by IDs and append attributes such as the severity, which allow complex filtering and
fancy coloring for better human readability.

<p align="center">
  <a title="edaa-org.github.io/pyEDAA.Reports" href="https://edaa-org.github.io/pyEDAA.Reports"><img height="275px" src="doc/_static/work-in-progress.png"/></a>
</p>

# Report Kinds

## Test Report Summary

* Test Suite
* Test Case
* Test Parameter

## Code Coverage Report

* Line Coverage
* Statement Coverage
* Branch Coverage
* Expression Coverage
* State Coverage
* Transition Coverage

## Functional Coverage

* Coverage Model
  * Dimension
  * Bin
    * Item
    * Range

## Synthesis

* Area/resources
* Timing

## Implementation

* Area/resources
* Timing

# Target input logs/formats

* ActiveHDL
* CoCoTb
* Diamond
* GHDL
* Icarus Verilog
* ISE
* ModelSim/QuestaSim
* nextpnr
* OSVVM
* RivieraPRO
* SymbiYosys
* Synplify
* Quartus
* Verilator
* Verilog-to-Routing
* Vivado
* VUnit
* Xcelium
* Yosys
* ...

# References

* [olofk/edalize](https://github.com/olofk/edalize/) (see `edalize.reporting`, `edalize.vivado_reporting`, `edalize.quartus_reporting`, `edalize.ise_reporting`, ...)
* [librecores/eda-log-parser](https://github.com/librecores/eda-log-parser)
* [SymbiFlow/fpga-tool-perf](https://github.com/SymbiFlow/fpga-tool-perf)
* [mattvenn/logLUTs](https://github.com/mattvenn/logLUTs)
* [tiagolascasas/Vivado-HLS-Report-Parser](https://github.com/tiagolascasas/Vivado-HLS-Report-Parser)
* [cuelang.org/](https://cuelang.org/)
  * [cuelang.org/docs/tutorials](https://cuelang.org/docs/tutorials/)
  * [cue-lang/cue#162](https://github.com/cue-lang/cue/issues/162)
    * [pypi.org/project/pycue](https://pypi.org/project/pycue/)
    * [philipdexter/pycue](https://github.com/philipdexter/pycue)
