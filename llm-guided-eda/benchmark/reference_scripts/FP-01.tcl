# 40% utilization floorplan, then report the resulting die/core geometry.
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O

set block [ord::get_db_block]
set dbu [$block getDefUnits]
set die [$block getDieArea]
set core [$block getCoreArea]
set cell_area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  set cell_area [expr {$cell_area + double([$m getWidth]) * [$m getHeight] / $dbu / $dbu}]
}
set core_area [expr {double([$core xMax] - [$core xMin]) * ([$core yMax] - [$core yMin]) / $dbu / $dbu}]

set f [open outputs/fp_geometry.txt w]
puts $f [format "DIE %.3f %.3f %.3f %.3f" [expr {double([$die xMin]) / $dbu}] [expr {double([$die yMin]) / $dbu}] \
  [expr {double([$die xMax]) / $dbu}] [expr {double([$die yMax]) / $dbu}]]
puts $f [format "CORE %.3f %.3f %.3f %.3f" [expr {double([$core xMin]) / $dbu}] [expr {double([$core yMin]) / $dbu}] \
  [expr {double([$core xMax]) / $dbu}] [expr {double([$core yMax]) / $dbu}]]
puts $f [format "UTIL %.2f" [expr {100.0 * $cell_area / $core_area}]]
close $f
