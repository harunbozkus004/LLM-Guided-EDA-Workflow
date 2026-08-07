# Wrong units: the margin is in ns (library time units), 80 asks for 80 ns.
estimate_parasitics -placement
repair_timing -hold -hold_margin 80
detailed_placement
