# Wrong order: "before" is counted before the stricter rules are applied.
proc drv_counts {} {
  return [list [sta::max_slew_violation_count] [sta::max_capacitance_violation_count] \
            [sta::max_fanout_violation_count]]
}
estimate_parasitics -placement
set before [drv_counts]
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
repair_design
detailed_placement
estimate_parasitics -placement
set after [drv_counts]
set fh [open outputs/drv_summary.txt w]
foreach key {max_slew max_capacitance max_fanout} b $before a $after { puts $fh "$key $b $a" }
close $fh
