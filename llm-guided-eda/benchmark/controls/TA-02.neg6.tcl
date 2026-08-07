# Too many paths: the 3 paths from reset instead of only the worst one.
report_checks -from [get_ports reset] -path_delay max -group_count 3 -endpoint_count 3 -digits 4 > outputs/reset_setup_path.rpt
