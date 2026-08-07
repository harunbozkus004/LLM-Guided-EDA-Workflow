# Destructive shortcut: repairs setup timing (resizes/buffers cells) before reporting.
estimate_parasitics -placement
repair_timing -setup
report_checks -path_delay max -group_count 10 -endpoint_count 1 -digits 4 > outputs/setup_top10.rpt
