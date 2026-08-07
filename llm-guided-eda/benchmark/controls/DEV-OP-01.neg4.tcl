# Wrong object: the limit is put on the input ports only, internal nets are untouched.
set_max_fanout 10 [all_inputs]
estimate_parasitics -placement
repair_design
detailed_placement
