# Wrong check type: the 10 worst hold paths.
estimate_parasitics -placement
report_checks -path_delay min -group_count 10 -digits 4 > outputs/setup_top10.rpt
