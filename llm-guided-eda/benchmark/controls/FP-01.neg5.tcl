# Wrong: utilization computed against the die area instead of the core area.
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2 -sites FreePDK45_38x28_10R_NP_162NW_34O
set block [ord::get_db_block]
set area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  set area [expr {$area + [ord::dbu_to_microns [$m getWidth]] * [ord::dbu_to_microns [$m getHeight]]}]
}
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set f [open outputs/fp_geometry.txt w]
puts $f [format "DIE %.3f %.3f %.3f %.3f" $dx0 $dy0 $dx1 $dy1]
puts $f [format "CORE %.3f %.3f %.3f %.3f" $cx0 $cy0 $cx1 $cy1]
puts $f [format "UTIL %.3f" [expr {100.0 * $area / (($dx1 - $dx0) * ($dy1 - $dy0))}]]
close $f
