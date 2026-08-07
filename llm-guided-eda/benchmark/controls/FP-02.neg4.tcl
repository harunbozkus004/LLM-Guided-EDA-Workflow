# Wrong order: tracks created before initialize_floorplan, which deletes them.
make_tracks
initialize_floorplan -die_area {0 0 120 100} -core_area {10 10 110 90} -sites FreePDK45_38x28_10R_NP_162NW_34O
