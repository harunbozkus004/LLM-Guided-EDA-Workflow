# Alternative: setup + hold repair with a small setup margin, then re-check timing.
estimate_parasitics -placement
repair_timing -repair_tns 100 -setup_margin 0.01
detailed_placement
estimate_parasitics -placement
report_worst_slack -max -digits 4
report_tns -digits 4
