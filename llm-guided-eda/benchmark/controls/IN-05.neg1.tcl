# Wrong: filler cells are included in the cell area (utilization comes out as 100%).
set block [ord::get_db_block]
set dbu [$block getDefUnits]
set area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  set area [expr {$area + double([$m getWidth]) * [$m getHeight] / ($dbu * $dbu)}]
}
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [join [lmap v [ord::get_die_area] {format %.2f $v}] { }]"
puts $fh "core_area [join [lmap v [ord::get_core_area] {format %.2f $v}] { }]"
puts $fh [format "cell_area %.2f" $area]
puts $fh [format "utilization %.2f" [expr {100.0 * $area / (($cx1 - $cx0) * ($cy1 - $cy0))}]]
close $fh
