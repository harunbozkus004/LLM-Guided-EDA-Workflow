# Wrong parasitics assumption: estimates placement RC although the task says analyze as loaded.
estimate_parasitics -placement
report_checks -from [get_ports reset] -path_delay max -digits 4 > outputs/reset_setup_path.rpt
