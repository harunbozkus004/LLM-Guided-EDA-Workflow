# Wrong structure: one buffer per load pin instead of one buffer per input port.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X1]
set i 0
foreach bt [$block getBTerms] {
  if {[$bt getIoType] != "INPUT" || [$bt getName] == "clk"} { continue }
  set net [$bt getNet]
  foreach it [$net getITerms] {
    set buf [odb::dbInst_create $block $master "ld_buf_$i"]
    set out [odb::dbNet_create $block "ld_buf_net_$i"]
    $it disconnect
    $it connect $out
    [$buf findITerm A] connect $net
    [$buf findITerm Z] connect $out
    set loc [[$it getInst] getLocation]
    $buf setLocation [lindex $loc 0] [lindex $loc 1]
    $buf setPlacementStatus PLACED
    incr i
  }
}
detailed_placement
