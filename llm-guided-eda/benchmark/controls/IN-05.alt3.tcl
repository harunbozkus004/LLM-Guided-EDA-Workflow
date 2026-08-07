# Alternative: fillers recognized by master class CORE_SPACER, area from instance bounding boxes,
# unrounded values straight from ord::get_die_area / get_core_area.
set block [ord::get_db_block]
set area 0.0
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getType] eq "CORE_SPACER"} { continue }
  set bb [$inst getBBox]
  set area [expr {$area + [ord::dbu_to_microns [$bb getDX]] * [ord::dbu_to_microns [$bb getDY]]}]
}
set core [ord::get_core_area]
set core_area [expr {([lindex $core 2] - [lindex $core 0]) * ([lindex $core 3] - [lindex $core 1])}]
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [ord::get_die_area]"
puts $fh "core_area $core"
puts $fh "cell_area $area"
puts $fh "utilization [expr {$area / $core_area * 100}]"
close $fh
