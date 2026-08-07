# Wrong: core given as origin + size (10 10 100 80) instead of corner coordinates.
initialize_floorplan -die_area {0 0 120 100} -core_area {10 10 100 80} \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
make_tracks
