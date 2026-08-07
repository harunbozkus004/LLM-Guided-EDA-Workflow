# Wrong location: each hand-made buffer is placed on its IO pin, outside the core area.
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X2]
set i 0
foreach bt [$block getBTerms] {
  if {[$bt getIoType] != "INPUT" || [$bt getName] == "clk"} { continue }
  set net [$bt getNet]
  set loads [$net getITerms]
  set buf [odb::dbInst_create $block $master "in_buf_$i"]
  set out [odb::dbNet_create $block "in_buf_net_$i"]
  foreach it $loads { $it disconnect; $it connect $out }
  [$buf findITerm A] connect $net
  [$buf findITerm Z] connect $out
  set bb [$bt getBBox]
  $buf setLocation [$bb xMin] [$bb yMin]
  $buf setPlacementStatus PLACED
  incr i
}
