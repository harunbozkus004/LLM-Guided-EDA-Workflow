# Post-CTS hold check on the session as loaded (propagated clock, no wire parasitics).
report_checks -path_delay min -group_count 3 -endpoint_count 1 -format full -digits 4 \
  > outputs/hold_paths.rpt
