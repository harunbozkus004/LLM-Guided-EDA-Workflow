# Mistake: hold slack instead of setup slack.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
report_worst_slack -min -digits 4 > outputs/wns_rcx.txt
