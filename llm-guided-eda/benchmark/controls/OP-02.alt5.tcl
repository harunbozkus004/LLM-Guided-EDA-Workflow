# Alternative: a generous 150 ps hold margin (setup is protected by the repair).
estimate_parasitics -placement
repair_timing -hold -hold_margin 0.15
detailed_placement
