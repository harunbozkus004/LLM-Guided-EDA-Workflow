# Wrong direction: paths ending at reset (an input port has none).
report_checks -to [get_ports reset] -path_delay max -digits 4 > outputs/reset_setup_path.rpt
