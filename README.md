# pyEDAA.Reports

Proposal to define an abstract model for outputs from EDA tools and logging libraries.

The main intended use case of pyEDAA.Reports is to import multiple log/report formats (raw logs, CSVs, YAML, JSON, etc.)
and provide a unified model that can generate reports using popular formats such as XUnit or Cobertura.
Since most vendors, CI services and monitoring tools support XML, the internals of pyEDAA.Reports are to be based on
XML transformations.

As an abstract model, the main capability of pyEDAA.Reports is handling messages using an structured format.
The readers categorize messages by IDs and append attributes such as the severity, which allow complex filtering and
fancy coloring for better human readability.

## Report Kinds

### Test Report Summary

- Test Suite
- Test Case
- Test Parameter

### Code Coverage Report

- Line Coverage
- Statement Coverage
- Branch Coverage
- Expression Coverage
- State Coverage
- Transition Coverage

### Functional Coverage

- Coverage Model
  - Dimension
  - Bin
    - Item
    - Range

### Synthesis

- Area/resources
- Timing

### Implementation

- Area/resources
- Timing

## Target input logs/formats

- ActiveHDL
- CoCoTb
- Diamond
- GHDL
- Icarus Verilog
- ISE
- ModelSim/QuestaSim
- nextpnr
- OSVVM
- RivieraPRO
- SymbiYosys
- Synplify
- Quartus
- Verilator
- Verilog-to-Routing
- Vivado
- VUnit
- Xcelium
- Yosys
- ...

# References

- [OSVB: Open Source Verification Report (OSVR)](https://umarcor.github.io/osvb/apis/logging.html#open-source-verification-report)
- [olofk/edalize](https://github.com/olofk/edalize/) (see `edalize.reporting`, `edalize.vivado_reporting`, `edalize.quartus_reporting`, `edalize.ise_reporting`, ...)
- [librecores/eda-log-parser](https://github.com/librecores/eda-log-parser)
- [SymbiFlow/fpga-tool-perf](https://github.com/SymbiFlow/fpga-tool-perf)
- [mattvenn/logLUTs](https://github.com/mattvenn/logLUTs)
- [tiagolascasas/Vivado-HLS-Report-Parser](https://github.com/tiagolascasas/Vivado-HLS-Report-Parser)
