# Detailed routing on metal2-metal10, then the total routed wirelength.
detailed_route -bottom_routing_layer metal2 -top_routing_layer metal10
set block [ord::get_db_block]
set total 0
foreach net [$block getNets] {
  set wire [$net getWire]
  if {$wire != "NULL"} { set total [expr {$total + [$wire getLength]}] }
}
set fh [open outputs/dr_wirelength.txt w]
puts $fh [format %.3f [expr {double($total) / [$block getDefUnits]}]]
close $fh
