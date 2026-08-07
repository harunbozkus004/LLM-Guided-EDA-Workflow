# Alternative: design repair first, then setup repair on all endpoints.
estimate_parasitics -placement
repair_design
repair_timing -setup -repair_tns 100
detailed_placement
