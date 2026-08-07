# Alternative: all endpoints with a 50 ps setup margin (lands near -0.31 ns TNS in this build).
estimate_parasitics -placement
repair_timing -setup -repair_tns 100 -setup_margin 0.05
detailed_placement
