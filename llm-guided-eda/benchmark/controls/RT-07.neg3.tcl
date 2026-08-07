# Mistake: SPEF extracted correctly, but the slack comes from the placement-based estimate.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
estimate_parasitics -placement
report_worst_slack -max -digits 4 > outputs/wns_rcx.txt
