# Shallow report: endpoint summary table instead of full path detail.
estimate_parasitics -placement
report_checks -path_delay max -group_count 10 -endpoint_count 1 -format end -digits 4 > outputs/setup_top10.rpt
