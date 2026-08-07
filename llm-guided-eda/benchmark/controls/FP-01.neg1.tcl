# Wrong: utilization given as a fraction (0.4 means 0.4% in this command), report otherwise correct.
initialize_floorplan -utilization 0.4 -aspect_ratio 1.0 -core_space 2 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
lassign [ord::get_die_area] dx0 dy0 dx1 dy1
lassign [ord::get_core_area] cx0 cy0 cx1 cy1
set f [open outputs/fp_geometry.txt w]
puts $f "DIE $dx0 $dy0 $dx1 $dy1"
puts $f "CORE $cx0 $cy0 $cx1 $cy1"
puts $f "UTIL [expr {[rsz::utilization] * 100.0}]"
close $f
