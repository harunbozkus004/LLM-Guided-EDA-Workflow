# Alternative: stricter limit and a shorter maximum wire length, then report the check.
set_max_fanout 8 [current_design]
estimate_parasitics -placement
repair_design -max_wire_length 300
detailed_placement
report_check_types -max_fanout -violators
