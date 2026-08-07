# Floorplan boxes and non-filler cell area computed from the database
# (report_design_area only prints rounded integers through the logger).
set block [ord::get_db_block]
set dbu [$block getDefUnits]
proc box_um {rect dbu} {
  set out {}
  foreach v [list [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]] {
    lappend out [format %.4f [expr {double($v) / $dbu}]]
  }
  return [join $out " "]
}
set die [$block getDieArea]
set core [$block getCoreArea]
set cell_area 0.0
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {[$master isFiller]} { continue }
  set cell_area [expr {$cell_area + double([$master getWidth]) * [$master getHeight] / ($dbu * $dbu)}]
}
set core_area [expr {double([$core xMax] - [$core xMin]) * ([$core yMax] - [$core yMin]) / ($dbu * $dbu)}]
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [box_um $die $dbu]"
puts $fh "core_area [box_um $core $dbu]"
puts $fh [format "cell_area %.4f" $cell_area]
puts $fh [format "utilization %.4f" [expr {100.0 * $cell_area / $core_area}]]
close $fh
