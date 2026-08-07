# Alternative: ORFS-style post-CTS repair (setup on every endpoint, then hold), padded
# legalization and timing reports with full clock expansion.
estimate_parasitics -placement
report_tns -digits 4
repair_timing -setup -repair_tns 100
repair_timing -hold
set_placement_padding -global -left 1 -right 1
detailed_placement
estimate_parasitics -placement
report_checks -path_delay max -format full_clock_expanded -digits 4
report_tns -digits 4
report_wns -digits 4
