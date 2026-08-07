# Alternative: combined setup + hold repair with a slightly larger hold margin, then re-check.
estimate_parasitics -placement
repair_timing -hold_margin 0.09
detailed_placement
estimate_parasitics -placement
report_worst_slack -min -digits 4
report_worst_slack -max -digits 4
