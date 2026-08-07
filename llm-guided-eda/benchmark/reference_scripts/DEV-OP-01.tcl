# Design-level fanout limit, buffer the offending nets, re-legalize.
set_max_fanout 10 [current_design]
estimate_parasitics -placement
repair_design
detailed_placement
