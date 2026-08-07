# Wrong value: a fanout limit of 16 leaves 16-load nets in place.
set_max_fanout 16 [current_design]
estimate_parasitics -placement
repair_design
detailed_placement
