# Alternative: express the margin as a hold clock uncertainty and repair to zero slack.
set_clock_uncertainty -hold 0.08 [all_clocks]
estimate_parasitics -placement
repair_timing -hold
detailed_placement
