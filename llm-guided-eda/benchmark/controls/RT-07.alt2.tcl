# Alternative: a placement estimate first (overridden by the SPEF), LEF resistances, report_wns.
estimate_parasitics -placement
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules -lef_res
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
report_wns -digits 4 > outputs/wns_rcx.txt
