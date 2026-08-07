# Mistake: the design is re-routed before extraction.
detailed_route -droute_end_iter 1
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
report_worst_slack -max -digits 4 > outputs/wns_rcx.txt
