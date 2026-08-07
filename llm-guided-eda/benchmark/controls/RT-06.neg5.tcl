# Mistake: wirelength estimated from the route-guide boxes instead of the global routes.
set block [ord::get_db_block]
set out [open outputs/clock_gr_wirelength.txt w]
foreach net [$block getNets] {
  if {[$net getSigType] != "CLOCK"} { continue }
  set total 0
  foreach g [$net getGuides] {
    set b [$g getBox]
    set total [expr {$total + max([$b xMax] - [$b xMin], [$b yMax] - [$b yMin])}]
  }
  puts $out "[$net getName] [expr {$total / double([$block getDefUnits])}]"
}
close $out
