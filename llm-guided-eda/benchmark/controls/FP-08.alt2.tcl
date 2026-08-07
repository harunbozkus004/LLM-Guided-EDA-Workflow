# Alternative order: power grid before the tap cells, then global connections re-applied.
initialize_floorplan -utilization 30 -aspect_ratio 1.0 -core_space {4 4 4 4} \
  -sites FreePDK45_38x28_10R_NP_162NW_34O
source platform/Nangate45.tracks
source platform/Nangate45.pdn.tcl
pdngen
tapcell -distance 15 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
global_connect
place_pins -hor_layers metal3 -ver_layers metal2
