# Wrong source: liberty cell areas, which this build rounds to integers (cells without a liberty model skipped).
set area 0.0
foreach cell [get_cells *] {
  if {[string match FILLCELL* [get_property $cell ref_name]]} { continue }
  if {[catch {get_property [get_lib_cells -of_objects $cell] area} a]} { continue }
  set area [expr {$area + $a}]
}
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set fh [open outputs/floorplan_summary.txt w]
puts $fh "die_area [join [lmap v [ord::get_die_area] {format %.2f $v}] { }]"
puts $fh "core_area [join [lmap v [ord::get_core_area] {format %.2f $v}] { }]"
puts $fh [format "cell_area %.2f" $area]
puts $fh [format "utilization %.2f" [expr {100.0 * $area / (($cx1 - $cx0) * ($cy1 - $cy0))}]]
close $fh
