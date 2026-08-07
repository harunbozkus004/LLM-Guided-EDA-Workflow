# Alternative: four-value core spacing {bottom top left right}, utilization from the resizer, extra harmless report.
initialize_floorplan -utilization 40 -aspect_ratio 1 -core_space {2 2 2 2} \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
report_design_area
set f [open outputs/fp_geometry.txt w]
puts $f "DIE [lmap v [ord::get_die_area] {format %.3f $v}]"
puts $f "CORE [lmap v [ord::get_core_area] {format %.3f $v}]"
puts $f "UTIL [format %.1f [expr {[rsz::utilization] * 100.0}]]%"
close $f
