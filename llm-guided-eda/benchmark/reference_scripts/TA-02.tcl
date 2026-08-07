# Worst setup path launched from input port reset (ideal clock, no wire parasitics).
report_checks -from [get_ports reset] -path_delay max -digits 4 > outputs/reset_setup_path.rpt
