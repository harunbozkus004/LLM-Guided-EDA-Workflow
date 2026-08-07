# Missing step: hold buffers are inserted but the placement is never re-legalized.
estimate_parasitics -placement
repair_timing -hold -hold_margin 0.08
