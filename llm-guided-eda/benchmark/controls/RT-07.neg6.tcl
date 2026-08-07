# Mistake: default report precision (2 decimals) instead of 4.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
report_worst_slack -max > outputs/wns_rcx.txt
