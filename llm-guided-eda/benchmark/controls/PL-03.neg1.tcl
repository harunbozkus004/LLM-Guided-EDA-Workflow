# Wrong definition: logic cells only (tap cells excluded) -> 7.71 % instead of 8.18 %.
set block [ord::get_db_block]
set core [$block getCoreArea]
set core_area [expr {double([$core xMax] - [$core xMin]) * ([$core yMax] - [$core yMin])}]
set cell_area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m getType] ne "CORE"} continue
  set cell_area [expr {$cell_area + double([$m getWidth]) * [$m getHeight]}]
}
set util [expr {100.0 * $cell_area / $core_area}]
set f [open outputs/utilization.txt w]
puts $f [format "utilization_percent: %.2f" $util]
puts $f "above_target: [expr {$util > 70.0 ? "yes" : "no"}]"
close $f
