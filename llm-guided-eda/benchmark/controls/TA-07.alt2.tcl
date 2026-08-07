# Alternative: compute all four numbers from the per-endpoint worst paths (path API)
# after reading the extracted SPEF back.
define_process_corner -ext_model_index 0 X
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
set wss 1e30
set tns 0.0
set n 0
foreach pe [find_timing_paths -path_delay max -group_count 100000 -endpoint_count 1] {
  set s [sta::time_sta_ui [$pe slack]]
  if {$s < $wss} { set wss $s }
  if {$s < 0} { set tns [expr {$tns + $s}]; incr n }
}
set pe [lindex [find_timing_paths -path_delay min -group_count 1] 0]
set whs [sta::time_sta_ui [$pe slack]]
set f [open outputs/signoff_summary.txt w]
puts $f "worst_setup_slack [format %.4f $wss]"
puts $f "total_negative_setup_slack [format %.4f $tns]"
puts $f "worst_hold_slack [format %.4f $whs]"
puts $f "setup_violating_endpoints $n"
close $f
