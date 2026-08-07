# Alternative: ORFS-style post-CTS repair -- setup on all endpoints first, then hold with margin.
estimate_parasitics -placement
repair_timing -setup -repair_tns 100
repair_timing -hold -hold_margin 0.08
detailed_placement
estimate_parasitics -placement
report_worst_slack -min -digits 4
report_worst_slack -max -digits 4
