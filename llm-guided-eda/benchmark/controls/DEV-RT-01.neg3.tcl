# Mistake: set_routing_layers is used, which detailed_route ignores, so the router still wires on metal1.
set_routing_layers -signal metal2-metal10
detailed_route
set block [ord::get_db_block]
set total 0
foreach net [$block getNets] {
  set w [$net getWire]
  if {$w != "NULL"} { set total [expr {$total + [$w getLength]}] }
}
set fh [open outputs/dr_wirelength.txt w]
puts $fh [expr {double($total) / [$block getDefUnits]}]
close $fh
