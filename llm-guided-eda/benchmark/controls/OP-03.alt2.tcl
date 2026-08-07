# Alternative: sizing and buffering only (no pin swapping / gate cloning) on all endpoints.
estimate_parasitics -placement
repair_timing -setup -repair_tns 100 -skip_pin_swap -skip_gate_cloning
detailed_placement
