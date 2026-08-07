# Hold repair with an 80 ps margin on placement-based parasitics, then re-legalize.
estimate_parasitics -placement
repair_timing -hold -hold_margin 0.08
detailed_placement
