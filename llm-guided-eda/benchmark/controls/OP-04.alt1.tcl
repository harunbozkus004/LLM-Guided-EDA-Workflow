# Alternative: count with the STA limit-check functions and over-repair with margins.
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
proc drv_counts {} {
  return [list [llength [sta::check_slew_limits NULL 1 NULL max]] \
            [llength [sta::check_capacitance_limits NULL 1 NULL max]] \
            [llength [sta::check_fanout_limits NULL 1 max]]]
}
estimate_parasitics -placement
set before [drv_counts]
repair_design -slew_margin 20 -cap_margin 20
detailed_placement
estimate_parasitics -placement
set after [drv_counts]
set fh [open outputs/drv_summary.txt w]
puts $fh "max_slew [lindex $before 0] [lindex $after 0]"
puts $fh "max_capacitance [lindex $before 1] [lindex $after 1]"
puts $fh "max_fanout [lindex $before 2] [lindex $after 2]"
close $fh
