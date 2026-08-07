# Wrong units: transition limit given in ps (50 means 50 ns here), so slews are never repaired.
set_max_transition 50 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
proc drv_counts {} {
  return [list [llength [sta::check_slew_limits NULL 1 NULL max]] \
            [llength [sta::check_capacitance_limits NULL 1 NULL max]] \
            [llength [sta::check_fanout_limits NULL 1 max]]]
}
estimate_parasitics -placement
set before [drv_counts]
repair_design
detailed_placement
estimate_parasitics -placement
set after [drv_counts]
set fh [open outputs/drv_summary.txt w]
foreach key {max_slew max_capacitance max_fanout} b $before a $after { puts $fh "$key $b $a" }
close $fh
