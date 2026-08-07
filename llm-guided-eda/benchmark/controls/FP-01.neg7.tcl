# Wrong: cell area from get_property <lib_cell> area, which returns 1 for every cell in this version (UTIL 28.8 instead of 41.35).
initialize_floorplan -utilization 40.0 -aspect_ratio 1 -core_space 2.0 -sites FreePDK45_38x28_10R_NP_162NW_34O
set area 0.0
foreach c [get_cells *] {
  set area [expr {$area + [get_property [get_lib_cells -of_objects $c] area]}]
}
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set util [expr {100.0 * $area / (($cx1 - $cx0) * ($cy1 - $cy0))}]
set f [open outputs/fp_geometry.txt w]
puts $f [format "DIE (%.3f, %.3f) (%.3f, %.3f)" $dx0 $dy0 $dx1 $dy1]
puts $f [format "CORE (%.3f, %.3f) (%.3f, %.3f)" $cx0 $cy0 $cx1 $cy1]
puts $f [format "UTIL %.3f%%" $util]
close $f
