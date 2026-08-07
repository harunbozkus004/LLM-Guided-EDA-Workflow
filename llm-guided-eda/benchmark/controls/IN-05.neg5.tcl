# Wrong units: die and core boxes written in database units instead of microns.
set block [ord::get_db_block]
set die [$block getDieArea]
set core [$block getCoreArea]
set util [rsz::utilization]
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [$die xMin] [$die yMin] [$die xMax] [$die yMax]"
puts $fh "core_area [$core xMin] [$core yMin] [$core xMax] [$core yMax]"
puts $fh [format "cell_area %.2f" [expr {[rsz::design_area] * 1e12}]]
puts $fh [format "utilization %.2f" [expr {$util * 100.0}]]
close $fh
