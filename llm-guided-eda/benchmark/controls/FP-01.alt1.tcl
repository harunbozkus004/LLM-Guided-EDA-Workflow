# Alternative: explicit die/core boxes sized from the total cell area; report via ord:: helpers.
set area 0.0
foreach inst [[ord::get_db_block] getInsts] {
  set m [$inst getMaster]
  set area [expr {$area + [ord::dbu_to_microns [$m getWidth]] * [ord::dbu_to_microns [$m getHeight]]}]
}
set side [expr {sqrt($area / 0.40)}]
initialize_floorplan -sites FreePDK45_38x28_10R_NP_162NW_34O \
  -die_area [list 0 0 [expr {$side + 4.0}] [expr {$side + 4.0}]] \
  -core_area [list 2 2 [expr {$side + 2.0}] [expr {$side + 2.0}]]
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set f [open outputs/fp_geometry.txt w]
puts $f [format "DIE %.3f %.3f %.3f %.3f" $dx0 $dy0 $dx1 $dy1]
puts $f [format "CORE %.3f %.3f %.3f %.3f" $cx0 $cy0 $cx1 $cy1]
puts $f "UTIL [expr {100.0 * $area / (($cx1 - $cx0) * ($cy1 - $cy0))}]"
close $f
