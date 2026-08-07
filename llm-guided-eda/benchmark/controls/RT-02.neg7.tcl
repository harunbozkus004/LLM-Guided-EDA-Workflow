# Mistake: the design is also detail-routed and the detailed-route wirelength is reported.
global_route
detailed_route
set block [ord::get_db_block]
set total 0
foreach net [$block getNets] {
  set w [$net getWire]
  if {$w != "NULL"} { set total [expr {$total + [$w getLength]}] }
}
set out [open outputs/grt_wirelength.txt w]
puts $out [expr {double($total) / [$block getDefUnits]}]
close $out
