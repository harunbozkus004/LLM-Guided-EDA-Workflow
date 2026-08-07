# Alternative: ORFS-style violation counters, an over-repair with a shorter maximum wire
# length, and the summary formatted with format.
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
proc drv_counts {} {
  return [list [sta::max_slew_violation_count] [sta::max_capacitance_violation_count] \
            [sta::max_fanout_violation_count]]
}
estimate_parasitics -placement
set before [drv_counts]
puts "before: $before"
repair_design -max_wire_length 200 -verbose
set_placement_padding -global -left 1 -right 1
detailed_placement
check_placement
estimate_parasitics -placement
set after [drv_counts]
puts "after: $after"
report_check_types -max_slew -max_capacitance -max_fanout -violators
set fh [open outputs/drv_summary.txt w]
foreach key {max_slew max_capacitance max_fanout} b $before a $after {
  puts $fh [format "%s %d %d" $key $b $a]
}
close $fh
