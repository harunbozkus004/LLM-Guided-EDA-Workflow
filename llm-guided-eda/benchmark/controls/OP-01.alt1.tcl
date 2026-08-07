# Alternative: insert BUF_X2 input buffers by hand with the database API, place each
# buffer on its first load and legalize afterwards (allowed, not required).
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X2]
set i 0
foreach bt [$block getBTerms] {
  if {[$bt getIoType] != "INPUT" || [$bt getName] == "clk"} { continue }
  set net [$bt getNet]
  set loads [$net getITerms]
  set buf [odb::dbInst_create $block $master "in_buf_$i"]
  set out [odb::dbNet_create $block "in_buf_net_$i"]
  foreach it $loads {
    $it disconnect
    $it connect $out
  }
  [$buf findITerm A] connect $net
  [$buf findITerm Z] connect $out
  set loc [[[lindex $loads 0] getInst] getLocation]
  $buf setLocation [lindex $loc 0] [lindex $loc 1]
  $buf setPlacementStatus PLACED
  incr i
}
detailed_placement
