# Forgot the clock: hand-made input buffering loops over every input port, clk included.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X2]
set i 0
foreach bt [$block getBTerms] {
  if {[$bt getIoType] != "INPUT"} { continue }
  set net [$bt getNet]
  set loads [$net getITerms]
  set buf [odb::dbInst_create $block $master "in_buf_$i"]
  set out [odb::dbNet_create $block "in_buf_net_$i"]
  foreach it $loads { $it disconnect; $it connect $out }
  [$buf findITerm A] connect $net
  [$buf findITerm Z] connect $out
  set loc [[[lindex $loads 0] getInst] getLocation]
  $buf setLocation [lindex $loc 0] [lindex $loc 1]
  $buf setPlacementStatus PLACED
  incr i
}
detailed_placement
