# Wrong count: violating paths (up to 100 per endpoint) instead of violating endpoints.
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
set f [open outputs/signoff_summary.txt w]
puts $f [format "worst_setup_slack %.4f" [worst_slack -max]]
puts $f [format "total_negative_setup_slack %.4f" [total_negative_slack -max]]
puts $f [format "worst_hold_slack %.4f" [worst_slack -min]]
set n 0
foreach pe [find_timing_paths -path_delay max -group_count 100000 -endpoint_count 100] { if {[$pe slack] < 0} { incr n } }
puts $f "setup_violating_endpoints $n"
close $f
