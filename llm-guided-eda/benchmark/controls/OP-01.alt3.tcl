# Alternative: hand-inserted BUF_X1 buffers via ODB, each placed at the centroid of its
# loads and not legalized (allowed by the task).
set block [ord::get_db_block]
set master [[ord::get_db] findMaster BUF_X1]
foreach port [all_inputs] {
  if {[get_full_name $port] == "clk"} { continue }
  set name [get_full_name $port]
  set bt [$block findBTerm $name]
  set net [$bt getNet]
  set loads [$net getITerms]
  set safe [string map {[ _ ] _} $name]
  set buf [odb::dbInst_create $block $master "ibuf_$safe"]
  set out [odb::dbNet_create $block "ibuf_net_$safe"]
  set sx 0; set sy 0
  foreach it $loads {
    set loc [[$it getInst] getLocation]
    set sx [expr {$sx + [lindex $loc 0]}]; set sy [expr {$sy + [lindex $loc 1]}]
    $it disconnect
    $it connect $out
  }
  [$buf findITerm A] connect $net
  [$buf findITerm Z] connect $out
  set n [llength $loads]
  $buf setLocation [expr {$sx / $n}] [expr {$sy / $n}]
  $buf setPlacementStatus PLACED
}
