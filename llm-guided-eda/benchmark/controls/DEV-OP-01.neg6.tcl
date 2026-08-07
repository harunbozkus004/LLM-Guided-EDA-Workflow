# Wrong cell: high-fanout nets split by hand with an inverter per load group (logic inverted).
set block [ord::get_db_block]
set inv [[ord::get_db] findMaster INV_X2]
set k 0
foreach net [$block getNets] {
  if {[$net getSigType] in {POWER GROUND} || [$net getName] == "clk"} { continue }
  set loads {}
  foreach it [$net getITerms] { if {[$it getIoType] == "INPUT"} { lappend loads $it } }
  if {[llength $loads] <= 10} { continue }
  for {set i 0} {$i < [llength $loads]} {incr i 8} {
    set b [odb::dbInst_create $block $inv "fo_inv_$k"]
    set bn [odb::dbNet_create $block "fo_inv_net_$k"]
    [$b findITerm A] connect $net
    [$b findITerm ZN] connect $bn
    foreach it [lrange $loads $i [expr {$i + 7}]] { $it disconnect; $it connect $bn }
    set loc [[[lindex $loads $i] getInst] getLocation]
    $b setLocation [lindex $loc 0] [lindex $loc 1]
    $b setPlacementStatus PLACED
    incr k
  }
}
detailed_placement
