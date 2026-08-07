# Destructive: re-initializes the floorplan (default 0 um margin) before placing the pins.
initialize_floorplan -utilization 30 -aspect_ratio 1 -core_space 10 -sites FreePDK45_38x28_10R_NP_162NW_34O
source platform/Nangate45.tracks
place_pins -hor_layers metal5 -ver_layers metal4 -min_distance 4
