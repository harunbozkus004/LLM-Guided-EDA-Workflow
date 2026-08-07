# Alternative: harmless timing/clock reports first, then a sorted netlist without tap cells (name pattern).
report_clock_properties
report_checks -path_delay max -group_count 1
write_verilog -sort -remove_cells "TAPCELL*" outputs/gcd_netlist.v
