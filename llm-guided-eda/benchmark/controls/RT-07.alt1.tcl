# Alternative: explicit process corner and extraction settings (the defaults), report redirect.
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules \
  -max_res 50 -coupling_threshold 0.1 -cc_model 10 -context_depth 5
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
report_worst_slack -max -digits 4 > outputs/wns_rcx.txt
