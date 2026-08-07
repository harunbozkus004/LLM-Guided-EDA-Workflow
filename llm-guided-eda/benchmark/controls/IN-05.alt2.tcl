# Alternative: fillers recognized by name, sizes converted with ord::dbu_to_microns.
set block [ord::get_db_block]
set area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[string match FILLCELL* [$m getName]]} { continue }
  set area [expr {$area + [ord::dbu_to_microns [$m getWidth]] * [ord::dbu_to_microns [$m getHeight]]}]
}
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set fh [open outputs/floorplan_summary.txt w]
puts $fh [format "die_area: %.3f %.3f %.3f %.3f" $dx0 $dy0 $dx1 $dy1]
puts $fh [format "core_area: %.3f %.3f %.3f %.3f" $cx0 $cy0 $cx1 $cy1]
puts $fh [format "cell_area: %.3f" $area]
puts $fh [format "utilization: %.3f" [expr {100.0 * $area / (($cx1 - $cx0) * ($cy1 - $cy0))}]]
close $fh
