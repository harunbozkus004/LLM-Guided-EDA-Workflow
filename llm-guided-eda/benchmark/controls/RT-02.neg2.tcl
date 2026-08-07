# Mistake: total length of the route-guide boxes instead of the routed wirelength.
global_route
set block [ord::get_db_block]
set total 0
foreach net [$block getNets] {
  foreach g [$net getGuides] {
    set b [$g getBox]
    set total [expr {$total + max([$b xMax] - [$b xMin], [$b yMax] - [$b yMin])}]
  }
}
set out [open outputs/grt_wirelength.txt w]
puts $out [expr {$total / double([$block getDefUnits])}]
close $out
