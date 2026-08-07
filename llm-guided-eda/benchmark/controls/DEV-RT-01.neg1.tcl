# Mistake: no routing layer range, so the router also wires on metal1.
detailed_route
set block [ord::get_db_block]
set total 0
foreach net [$block getNets] {
  set wire [$net getWire]
  if {$wire != "NULL"} { set total [expr {$total + [$wire getLength]}] }
}
set fh [open outputs/dr_wirelength.txt w]
puts $fh [expr {double($total) / [$block getDefUnits]}]
close $fh
