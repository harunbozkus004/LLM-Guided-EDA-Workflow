# HPWL from instance bounding boxes (as in some regression scripts) instead of pin locations.
proc bbox_hpwl {} {
  set block [ord::get_db_block]
  set total 0
  foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} continue
    set x0 1e30; set y0 1e30; set x1 -1e30; set y1 -1e30
    foreach it [$net getITerms] {
      set b [[$it getInst] getBBox]
      set x0 [expr {min($x0, [$b xMin])}]; set y0 [expr {min($y0, [$b yMin])}]
      set x1 [expr {max($x1, [$b xMax])}]; set y1 [expr {max($y1, [$b yMax])}]
    }
    foreach bt [$net getBTerms] {
      foreach bp [$bt getBPins] {
        set b [$bp getBBox]
        set x0 [expr {min($x0, [$b xMin])}]; set y0 [expr {min($y0, [$b yMin])}]
        set x1 [expr {max($x1, [$b xMax])}]; set y1 [expr {max($y1, [$b yMax])}]
      }
    }
    if {$x0 < 1e30} { set total [expr {$total + $x1 - $x0 + $y1 - $y0}] }
  }
  return [expr {$total / 2000.0}]
}
set before [bbox_hpwl]
improve_placement
set after [bbox_hpwl]
set f [open outputs/hpwl.txt w]
puts $f [format "hpwl_before_um: %.2f" $before]
puts $f [format "hpwl_after_um: %.2f" $after]
close $f
