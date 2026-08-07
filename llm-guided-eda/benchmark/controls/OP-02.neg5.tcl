# Setup sacrificed: an oversized hold margin with -allow_setup_violations degrades setup by ~19 ps.
estimate_parasitics -placement
repair_timing -hold -hold_margin 0.15 -allow_setup_violations
detailed_placement
