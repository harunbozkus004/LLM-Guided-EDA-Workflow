# Alternative: parenthesised/comma-separated coordinates, utilization from the resizer with a percent sign.
initialize_floorplan -utilization 40.0 -aspect_ratio 1 -core_space 2.0 -sites FreePDK45_38x28_10R_NP_162NW_34O
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set f [open outputs/fp_geometry.txt w]
puts $f [format "DIE (%.3f, %.3f) (%.3f, %.3f)" $dx0 $dy0 $dx1 $dy1]
puts $f [format "CORE (%.3f, %.3f) (%.3f, %.3f)" $cx0 $cy0 $cx1 $cy1]
puts $f [format "UTIL %.3f%%" [expr {100.0 * [rsz::utilization]}]]
close $f
