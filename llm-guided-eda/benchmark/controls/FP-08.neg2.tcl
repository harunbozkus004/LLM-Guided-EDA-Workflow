# Wrong order: tracks created before initialize_floorplan (which removes them) -> pin placement fails.
make_tracks
initialize_floorplan -utilization 30 -aspect_ratio 1.0 -core_space 4 \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
place_pins -hor_layers metal3 -ver_layers metal2
tapcell -distance 15 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
source platform/Nangate45.pdn.tcl
pdngen
