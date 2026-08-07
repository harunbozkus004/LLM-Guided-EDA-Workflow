# Wrong: utilization computed against the die area instead of the core area.
set core_util [rsz::utilization]
set area [expr {[rsz::design_area] * 1e12}]
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [join [lmap v [ord::get_die_area] {format %.2f $v}] { }]"
puts $fh "core_area [join [lmap v [ord::get_core_area] {format %.2f $v}] { }]"
puts $fh [format "cell_area %.2f" $area]
puts $fh [format "utilization %.2f" [expr {100.0 * $area / (($dx1 - $dx0) * ($dy1 - $dy0))}]]
close $fh
