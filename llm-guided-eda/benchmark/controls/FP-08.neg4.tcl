# Wrong value: utilization given as a fraction (0.3 = 0.3%).
initialize_floorplan -utilization 0.3 -aspect_ratio 1.0 -core_space 4 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
source platform/Nangate45.tracks
place_pins -hor_layers metal3 -ver_layers metal2
tapcell -distance 15 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
source platform/Nangate45.pdn.tcl
pdngen
