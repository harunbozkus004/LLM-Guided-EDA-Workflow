# Several paths per endpoint: the 10 worst paths are all to the same output.
estimate_parasitics -placement
report_checks -path_delay max -group_count 10 -endpoint_count 10 -digits 4 > outputs/setup_top10.rpt
