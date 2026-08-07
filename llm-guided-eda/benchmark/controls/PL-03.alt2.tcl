# Alternative: core area from the placement rows, cell area from logic and well-tap masters.
set block [ord::get_db_block]
set row_area 0.0
foreach row [$block getRows] {
  set b [$row getBBox]
  set row_area [expr {$row_area + double([$b xMax] - [$b xMin]) * ([$b yMax] - [$b yMin])}]
}
set area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m getType] in {CORE CORE_WELLTAP}} {
    set area [expr {$area + double([$m getWidth]) * [$m getHeight]}]
  }
}
set pct [expr {$area / $row_area * 100.0}]
set f [open outputs/utilization.txt w]
puts $f "# placement utilization check"
puts $f "utilization_percent: [format %.2f $pct]"
puts $f "above_target: [expr {$pct > 70.0 ? {yes} : {no}}]"
close $f
