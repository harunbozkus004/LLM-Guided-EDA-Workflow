# Complete floorplan stage: floorplan, tracks, IO pins, tap cells, power grid.
initialize_floorplan -utilization 30 -aspect_ratio 1.0 -core_space 4 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
# initialize_floorplan removes tracks, so they are created afterwards (place_pins needs them)
source platform/Nangate45.tracks
place_pins -hor_layers metal3 -ver_layers metal2
tapcell -distance 15 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
# taps first: the global connections made by the PDN script then include them
source platform/Nangate45.pdn.tcl
pdngen
