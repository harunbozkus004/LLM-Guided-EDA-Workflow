# Alternative: micron arithmetic via ord::get_core_area / ord::dbu_to_microns; percent sign and upper-case answer.
lassign [ord::get_core_area] x0 y0 x1 y1
set core_um2 [expr {($x1 - $x0) * ($y1 - $y0)}]
set cell_um2 0.0
foreach inst [[ord::get_db_block] getInsts] {
  set m [$inst getMaster]
  set cell_um2 [expr {$cell_um2 + [ord::dbu_to_microns [$m getWidth]] * [ord::dbu_to_microns [$m getHeight]]}]
}
set u [expr {$cell_um2 / $core_um2 * 100}]
set fh [open "outputs/utilization.txt" w]
puts $fh "utilization_percent: [format %.2f $u]%"
puts $fh "above_target: [expr {$u > 70 ? "YES" : "NO"}]"
close $fh
