# Alternative: redundant set_propagated_clock, extra columns and options, 6 decimals.
set_propagated_clock [all_clocks]
report_checks -path_delay min -group_count 3 -endpoint_count 1 -unique_paths_to_endpoint -sort_by_slack \
  -fields {capacitance slew fanout input_pin nets} -digits 6 > outputs/hold_paths.rpt
