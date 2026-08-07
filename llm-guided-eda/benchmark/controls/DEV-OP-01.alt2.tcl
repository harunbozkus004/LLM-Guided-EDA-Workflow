# Alternative: limit applied and repaired without parasitic estimates (fanout does not depend on them).
set_max_fanout 10 [current_design]
repair_design
detailed_placement
report_check_types -max_fanout
