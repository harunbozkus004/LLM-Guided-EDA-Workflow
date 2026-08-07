# Incomplete: tracks only for the signal-routing layers metal2-metal6.
initialize_floorplan -die_area {0 0 120 100} -core_area {10 10 110 90} -sites FreePDK45_38x28_10R_NP_162NW_34O
foreach l {metal2 metal3 metal4 metal5 metal6} { make_tracks $l }
