# Wrong: CORE derived from the die area minus the requested spacing instead of the stored (row) core.
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2 -sites FreePDK45_38x28_10R_NP_162NW_34O
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
set cx0 [expr {$dx0 + 2}]; set cy0 [expr {$dy0 + 2}]; set cx1 [expr {$dx1 - 2}]; set cy1 [expr {$dy1 - 2}]
set f [open outputs/fp_geometry.txt w]
puts $f [format "DIE %.3f %.3f %.3f %.3f" $dx0 $dy0 $dx1 $dy1]
puts $f [format "CORE %.3f %.3f %.3f %.3f" $cx0 $cy0 $cx1 $cy1]
puts $f [format "UTIL %.3f" [expr {[rsz::utilization] * 100.0}]]
close $f
