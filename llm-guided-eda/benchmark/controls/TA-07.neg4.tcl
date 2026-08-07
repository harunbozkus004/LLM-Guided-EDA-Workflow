# Output in the wrong place: the SPEF is written to the run directory, not outputs/.
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef gcd.spef
read_spef gcd.spef
set f [open outputs/signoff_summary.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f [format "worst_hold_slack %.4f" [worst_slack -min]]
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
