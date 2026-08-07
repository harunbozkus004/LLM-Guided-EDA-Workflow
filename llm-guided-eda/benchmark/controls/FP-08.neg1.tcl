# Wrong order: tap cells inserted after the grid without reconnecting -> taps float.
initialize_floorplan -utilization 30 -aspect_ratio 1.0 -core_space 4 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
source platform/Nangate45.tracks
place_pins -hor_layers metal3 -ver_layers metal2
source platform/Nangate45.pdn.tcl
pdngen
tapcell -distance 15 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
