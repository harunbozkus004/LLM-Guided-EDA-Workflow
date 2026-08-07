# Alternative: expanded format with extra columns, explicit uniqueness and sorting options.
estimate_parasitics -placement
report_checks -path_delay max -group_count 10 -endpoint_count 1 -unique_paths_to_endpoint \
  -sort_by_slack -format full_clock_expanded -fields {slew cap input_pin net} -digits 4 \
  > outputs/setup_top10.rpt
