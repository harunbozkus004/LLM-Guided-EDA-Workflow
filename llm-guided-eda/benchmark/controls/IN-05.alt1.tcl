# Alternative: the resizer's utilization/design area (fillers excluded, SI units) and the ord area helpers.
# (rsz::utilization must come first: rsz::design_area alone crashes this build.)
set util_pct [expr {[rsz::utilization] * 100.0}]
set area_um2 [expr {[rsz::design_area] * 1e12}]
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [join [lmap v [ord::get_die_area] {format %.2f $v}] { }]"
puts $fh "core_area [join [lmap v [ord::get_core_area] {format %.2f $v}] { }]"
puts $fh [format "cell_area %.2f" $area_um2]
puts $fh [format "utilization %.2f" $util_pct]
close $fh
