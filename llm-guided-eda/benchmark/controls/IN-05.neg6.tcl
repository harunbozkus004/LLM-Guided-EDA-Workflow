# Tcl integer division: database units divided by an integer DBU truncate every value.
set block [ord::get_db_block]
set dbu [$block getDefUnits]
set die [$block getDieArea]
set core [$block getCoreArea]
set area 0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m isFiller]} { continue }
  incr area [expr {[$m getWidth] * [$m getHeight] / ($dbu * $dbu)}]
}
set core_area [expr {([$core xMax] - [$core xMin]) * ([$core yMax] - [$core yMin]) / ($dbu * $dbu)}]
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [expr {[$die xMin] / $dbu}] [expr {[$die yMin] / $dbu}] [expr {[$die xMax] / $dbu}] [expr {[$die yMax] / $dbu}]"
puts $fh "core_area [expr {[$core xMin] / $dbu}] [expr {[$core yMin] / $dbu}] [expr {[$core xMax] / $dbu}] [expr {[$core yMax] / $dbu}]"
puts $fh [format "cell_area %.2f" $area]
puts $fh [format "utilization %.2f" [expr {100.0 * $area / $core_area}]]
close $fh
