# Wrong check type: hold (min-delay) path from reset.
report_checks -from [get_ports reset] -path_delay min -digits 4 > outputs/reset_setup_path.rpt
