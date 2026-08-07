# Several paths per endpoint: -endpoint_count 3 repeats the worst endpoint.
report_checks -path_delay min -group_count 3 -endpoint_count 3 -digits 4 > outputs/hold_paths.rpt
