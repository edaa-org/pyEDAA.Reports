# pyEDAA.Reports

Proposal to define an XML-based logging format for outputs from EDA tools and logging libraries.

## Report Kinds

### Test Report Summary

* Test Suite
* Test Case
* Test Parameter

### Code Coverage Report

* Line Coverage
* Statement Coverage
* Branch Coverage
* Expression Coverage
* State Coverage
* Transition Coverage

### Functional Coverage

* Coverage Model
  * Dimension
  * Bin
    * Item
    * Range

### Synthesis

* Area/resources
* Timing

### Implementation

* Area/resources
* Timing

# References

- [OSVB: Open Source Verification Report (OSVR)](https://umarcor.github.io/osvb/apis/logging.html#open-source-verification-report)
- [olofk/edalize](https://github.com/olofk/edalize/) (see `edalize.reporting`, `edalize.vivado_reporting`, `edalize.quartus_reporting`, `edalize.ise_reporting`, ...)
- [SymbiFlow/fpga-tool-perf](https://github.com/SymbiFlow/fpga-tool-perf)
- [mattvenn/logLUTs](https://github.com/mattvenn/logLUTs)
- [tiagolascasas/Vivado-HLS-Report-Parser](https://github.com/tiagolascasas/Vivado-HLS-Report-Parser)
