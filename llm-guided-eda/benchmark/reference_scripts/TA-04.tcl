# Placement-estimated RC, then the 10 worst setup paths (one per endpoint).
estimate_parasitics -placement
report_checks -path_delay max -group_count 10 -endpoint_count 1 -digits 4 > outputs/setup_top10.rpt
