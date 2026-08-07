# Alternative: remove the existing repair buffers first (recommended before repair_design),
# then repair against the fanout limit, legalize with padding and verify.
remove_buffers
set_max_fanout 10 [current_design]
estimate_parasitics -placement
repair_design
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_check_types -max_fanout -violators
