# Mistake: total left in database units.
detailed_route -bottom_routing_layer metal2 -top_routing_layer metal10
set total 0
foreach net [[ord::get_db_block] getNets] {
  set w [$net getWire]
  if {$w != "NULL"} { set total [expr {$total + [$w getLength]}] }
}
set fh [open outputs/dr_wirelength.txt w]
puts $fh $total
close $fh
