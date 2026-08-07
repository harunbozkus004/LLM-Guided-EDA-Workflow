# Wrong: width and height swapped (die 100 x 120).
initialize_floorplan -die_area {0 0 100 120} -core_area {10 10 90 110} \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
make_tracks
