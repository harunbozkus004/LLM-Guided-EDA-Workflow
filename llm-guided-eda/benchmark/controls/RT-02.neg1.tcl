# Mistake: half-perimeter wirelength (a placement estimate) instead of the global-route wirelength.
global_route
set block [ord::get_db_block]
set total 0.0
foreach net [$block getNets] {
  if {[$net isSpecial] || [$net getSigType] in {POWER GROUND}} { continue }
  set xs {}
  set ys {}
  foreach it [$net getITerms] {
    set b [$it getBBox]
    lappend xs [expr {([$b xMin] + [$b xMax]) / 2}]
    lappend ys [expr {([$b yMin] + [$b yMax]) / 2}]
  }
  foreach bt [$net getBTerms] {
    set b [$bt getBBox]
    lappend xs [expr {([$b xMin] + [$b xMax]) / 2}]
    lappend ys [expr {([$b yMin] + [$b yMax]) / 2}]
  }
  if {[llength $xs] < 2} { continue }
  set xs [lsort -integer $xs]
  set ys [lsort -integer $ys]
  set total [expr {$total + [lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]}]
}
set out [open outputs/grt_wirelength.txt w]
puts $out [expr {$total / double([$block getDefUnits])}]
close $out
