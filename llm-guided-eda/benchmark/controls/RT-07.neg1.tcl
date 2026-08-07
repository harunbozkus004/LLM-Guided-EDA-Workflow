# Mistake: the SPEF is written but never read back, so timing ignores the extracted parasitics.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
report_worst_slack -max -digits 4 > outputs/wns_rcx.txt
