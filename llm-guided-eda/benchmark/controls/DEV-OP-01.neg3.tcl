# Missing step: fanout repaired but the placement is never re-legalized.
set_max_fanout 10 [current_design]
estimate_parasitics -placement
repair_design
