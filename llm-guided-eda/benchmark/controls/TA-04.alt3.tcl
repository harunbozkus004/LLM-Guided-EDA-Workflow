# Alternative: redundant wire-RC setup, default path type, full_clock format, sorted by slack.
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal6
estimate_parasitics -placement
report_checks -group_count 10 -format full_clock -sort_by_slack -digits 4 > outputs/setup_top10.rpt
