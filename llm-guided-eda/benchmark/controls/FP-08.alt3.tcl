# Alternative order: taps and power grid before the pins, make_tracks, random pin placement.
initialize_floorplan -utilization 30.0 -aspect_ratio 1 -core_space 4.0 -sites FreePDK45_38x28_10R_NP_162NW_34O
make_tracks
tapcell -distance 15 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
source platform/Nangate45.pdn.tcl
pdngen
place_pins -hor_layers metal3 -ver_layers metal2 -random
