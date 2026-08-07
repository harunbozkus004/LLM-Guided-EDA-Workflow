# Wrong clock assumption: switches the propagated clock back to ideal before reporting.
unset_propagated_clock [all_clocks]
report_checks -path_delay min -group_count 3 -digits 4 > outputs/hold_paths.rpt
