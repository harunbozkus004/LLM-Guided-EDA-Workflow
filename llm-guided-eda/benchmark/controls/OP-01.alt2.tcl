# Alternative: buffer_ports with explicit options, then an (allowed) legalization and checks.
buffer_ports -inputs -buffer_cell BUF_X4 -max_utilization 70
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement -verbose
report_design_area
