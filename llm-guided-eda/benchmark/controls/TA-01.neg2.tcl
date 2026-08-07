# Wrong parasitics assumption: estimates placement RC although the task says to analyze as loaded.
estimate_parasitics -placement
report_checks -path_delay min -group_count 3 -digits 4 > outputs/hold_paths.rpt
