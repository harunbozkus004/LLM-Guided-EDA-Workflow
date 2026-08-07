# Mistake: half-perimeter (bounding-box) wirelength of each clock net.
set block [ord::get_db_block]
set out [open outputs/clock_gr_wirelength.txt w]
foreach net [$block getNets] {
  if {[$net getSigType] != "CLOCK"} { continue }
  set xs {}; set ys {}
  foreach it [$net getITerms] { lappend xs [lindex [$it getAvgXY] 1]; lappend ys [lindex [$it getAvgXY] 2] }
  foreach bt [$net getBTerms] { set b [$bt getBBox]; lappend xs [$b xCenter]; lappend ys [$b yCenter] }
  set xs [lsort -integer $xs]; set ys [lsort -integer $ys]
  set hp [expr {([lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]) / double([$block getDefUnits])}]
  puts $out "[$net getName] $hp"
}
close $out
