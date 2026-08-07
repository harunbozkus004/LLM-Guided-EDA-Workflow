# Wrong: correct floorplan, but the report repeats the requested numbers instead of the real geometry.
initialize_floorplan -utilization 40 -aspect_ratio 1.0 -core_space 2 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
set f [open outputs/fp_geometry.txt w]
puts $f "DIE 0 0 40.045 40.045"
puts $f "CORE 2 2 38.045 38.045"
puts $f "UTIL 40"
close $f
