# Alternative: per-layer make_tracks with explicit pitches/offsets (the platform track definition written inline).
initialize_floorplan -die_area {0 0 120 100} -core_area {10 10 110 90} -sites FreePDK45_38x28_10R_NP_162NW_34O
make_tracks metal1 -x_offset 0.095 -x_pitch 0.19 -y_offset 0.07 -y_pitch 0.14
make_tracks metal2 -x_offset 0.095 -x_pitch 0.19 -y_offset 0.07 -y_pitch 0.14
make_tracks metal3 -x_offset 0.095 -x_pitch 0.19 -y_offset 0.07 -y_pitch 0.14
make_tracks metal4 -x_offset 0.095 -x_pitch 0.28 -y_offset 0.07 -y_pitch 0.28
make_tracks metal5 -x_offset 0.095 -x_pitch 0.28 -y_offset 0.07 -y_pitch 0.28
make_tracks metal6 -x_offset 0.095 -x_pitch 0.28 -y_offset 0.07 -y_pitch 0.28
make_tracks metal7 -x_offset 0.095 -x_pitch 0.8 -y_offset 0.07 -y_pitch 0.8
make_tracks metal8 -x_offset 0.095 -x_pitch 0.8 -y_offset 0.07 -y_pitch 0.8
make_tracks metal9 -x_offset 0.095 -x_pitch 1.6 -y_offset 0.07 -y_pitch 1.6
make_tracks metal10 -x_offset 0.095 -x_pitch 1.6 -y_offset 0.07 -y_pitch 1.6
