# Builds the benchmark starting states for gcd on Nangate45.
#
# Adapted from OpenROAD's own regression flow (third_party/OpenROAD/test/flow.tcl,
# gcd_nangate45.tcl and Nangate45.vars at commit 0922eecb9). Every stage is
# checkpointed with write_db; the run is deterministic (single thread).
#
# Run from a directory containing symlinks platform/ -> Nangate45 platform and
# design/ -> benchmark/designs/gcd, with a writable states/ directory.

set_thread_count 1

# ---- synth: netlist linked, no floorplan --------------------------------
read_lef platform/Nangate45_tech.lef
read_lef platform/Nangate45_stdcell.lef
read_liberty platform/Nangate45_typ.lib
read_verilog design/gcd.v
link_design gcd
read_sdc design/gcd.sdc
write_db states/synth.odb

# ---- fp_init: die/core + rows + routing tracks only ----------------------
initialize_floorplan -site FreePDK45_38x28_10R_NP_162NW_34O \
  -die_area {0 0 100.13 100.8} \
  -core_area {10.07 11.2 90.25 91}
source platform/Nangate45.tracks
write_db states/fp_init.odb

# ---- floorplan: + buffer removal, random IO pins, tapcells, PDN -------------
remove_buffers
place_pins -random -hor_layers metal3 -ver_layers metal2
tapcell -distance 120 -tapcell_master TAPCELL_X1 -endcap_master TAPCELL_X1
source platform/Nangate45.pdn.tcl
pdngen
write_db states/floorplan.odb

# ---- gplaced: global placement only (not legalized) ----------------------
set_global_routing_layer_adjustment metal2-metal10 0.5
set_routing_layers -signal metal2-metal10 -clock metal6-metal10
global_placement -routability_driven -density 0.3 -pad_left 2 -pad_right 2
place_pins -hor_layers metal3 -ver_layers metal2
write_db states/gplaced.odb

# ---- placed: design repair + legalized detailed placement (pre-CTS) ----------
source platform/Nangate45.rc
set_wire_rc -signal -layer metal3
set_wire_rc -clock -layer metal6
set_dont_use {CLKBUF_* AOI211_X1 OAI211_X1}
estimate_parasitics -placement
repair_design
repair_tie_fanout -separation 5 LOGIC0_X1/Z
repair_tie_fanout -separation 5 LOGIC1_X1/Z
set_placement_padding -global -left 1 -right 1
detailed_placement
write_db states/placed.odb

# ---- cts: clock tree + legalization ---------------------------------------
repair_clock_inverters
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4 \
  -sink_clustering_enable -sink_clustering_max_diameter 100
repair_clock_nets
detailed_placement
write_db states/cts.odb

# ---- grouted: post-CTS timing repair + global routing ---------------------------
set_propagated_clock [all_clocks]
estimate_parasitics -placement
repair_timing -skip_gate_cloning
detailed_placement
pin_access -bottom_routing_layer metal2 -top_routing_layer metal10
global_route -guide_file states/gcd.route_guide -congestion_iterations 100
write_db states/grouted.odb

# ---- routed: fillers + detailed routing --------------------------------------
filler_placement FILLCELL*
check_placement
pin_access -bottom_routing_layer metal2 -top_routing_layer metal10
detailed_route -output_drc states/route_drc.rpt -no_pin_access \
  -bottom_routing_layer metal2 -top_routing_layer metal10 -verbose 0
puts "BUILD_STATES drvs=[detailed_route_num_drvs]"
write_db states/routed.odb
puts "BUILD_STATES done"
