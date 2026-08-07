# Alternative: half of the violating endpoints, two passes, no gate cloning.
estimate_parasitics -placement
repair_timing -setup -repair_tns 50 -skip_gate_cloning
detailed_placement
estimate_parasitics -placement
repair_timing -setup -repair_tns 50 -skip_gate_cloning
detailed_placement
