# Alternative: compute the core size from the cell area and give explicit die/core boxes.
set block [ord::get_db_block]
set dbu [$block getDefUnits]
set area 0.0
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  set area [expr {$area + double([$m getWidth]) * [$m getHeight] / $dbu / $dbu}]
}
set side [expr {sqrt($area / 0.35)}]
set sp 5.0
initialize_floorplan -site FreePDK45_38x28_10R_NP_162NW_34O \
  -die_area [list 0 0 [expr {$side + 2 * $sp}] [expr {$side + 2 * $sp}]] \
  -core_area [list $sp $sp [expr {$side + $sp}] [expr {$side + $sp}]]
make_tracks
