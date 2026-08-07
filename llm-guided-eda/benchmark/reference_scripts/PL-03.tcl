# Utilization = area of all placed instances (logic + tap cells) / core area.
set block [ord::get_db_block]
set core [$block getCoreArea]
set core_area [expr {double([$core xMax] - [$core xMin]) * ([$core yMax] - [$core yMin])}]
set cell_area 0.0
foreach inst [$block getInsts] {
  if {[$inst getPlacementStatus] ni {PLACED FIRM LOCKED COVER}} continue
  set m [$inst getMaster]
  set cell_area [expr {$cell_area + double([$m getWidth]) * [$m getHeight]}]
}
set util [expr {100.0 * $cell_area / $core_area}]
set f [open outputs/utilization.txt w]
puts $f [format "utilization_percent: %.2f" $util]
puts $f "above_target: [expr {$util > 70.0 ? "yes" : "no"}]"
close $f
