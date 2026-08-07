# Alternative: no explicit process corner, explicit default extraction options,
# values parsed from the standard reports and the count from the path API.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules -corner_cnt 1 \
  -max_res 50 -coupling_threshold 0.1
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
with_output_to_variable rpt { report_worst_slack -max -digits 6 }
regexp {worst slack\s+(\S+)} $rpt -> wss
with_output_to_variable rpt { report_tns -digits 6 }
regexp {tns\s+(\S+)} $rpt -> tns
with_output_to_variable rpt { report_worst_slack -min -digits 6 }
regexp {worst slack\s+(\S+)} $rpt -> whs
set n 0
foreach pe [find_timing_paths -path_delay max -group_count 100000 -endpoint_count 1 -slack_max 0] {
  if {[$pe slack] < 0} { incr n }
}
set f [open outputs/signoff_summary.txt w]
puts $f "worst_setup_slack [format %.4f $wss]"
puts $f "total_negative_setup_slack [format %.4f $tns]"
puts $f "worst_hold_slack [format %.4f $whs]"
puts $f "setup_violating_endpoints $n"
close $f
