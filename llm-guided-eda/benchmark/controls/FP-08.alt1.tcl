# Alternative: explicit die/core sized for 30% utilization, LEF tracks, annealing pins,
# separate endcap/tap commands and the grid written inline.
set area 0.0
foreach inst [[ord::get_db_block] getInsts] {
  set m [$inst getMaster]
  set area [expr {$area + [ord::dbu_to_microns [$m getWidth]] * [ord::dbu_to_microns [$m getHeight]]}]
}
set side [expr {sqrt($area / 0.30)}]
initialize_floorplan -site FreePDK45_38x28_10R_NP_162NW_34O \
  -die_area [list 0 0 [expr {$side + 8}] [expr {$side + 8}]] \
  -core_area [list 4 4 [expr {$side + 4}] [expr {$side + 4}]]
make_tracks
place_pins -hor_layers metal3 -ver_layers metal2 -annealing
place_endcaps -endcap_vertical TAPCELL_X1
place_tapcells -master TAPCELL_X1 -distance 15
add_global_connection -net VDD -pin_pattern {^VDD$} -power
add_global_connection -net VSS -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name grid -voltage_domains CORE
add_pdn_stripe -grid grid -layer metal1 -width 0.17 -followpins
add_pdn_stripe -grid grid -layer metal4 -width 0.48 -pitch 56.0 -offset 2
add_pdn_stripe -grid grid -layer metal7 -width 1.40 -pitch 40.0 -offset 2
add_pdn_connect -grid grid -layers {metal1 metal4}
add_pdn_connect -grid grid -layers {metal4 metal7}
pdngen
