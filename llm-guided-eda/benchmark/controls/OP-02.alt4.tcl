# Alternative: hold margin with a buffer budget, verbose repair, verification reports afterwards.
estimate_parasitics -placement
report_checks -path_delay min -format full_clock_expanded -digits 4
repair_timing -hold -hold_margin 0.085 -max_buffer_percent 30 -verbose
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_checks -path_delay min -format full_clock_expanded -digits 4
report_tns -digits 4
