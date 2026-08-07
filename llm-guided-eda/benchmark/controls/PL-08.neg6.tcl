# Optimization plus an IO pin re-placement: the pins are not allowed to move.
proc total_hpwl {} {
  set block [ord::get_db_block]
  set total 0.0
  foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} continue
    set xs {}; set ys {}
    foreach iterm [$net getITerms] {
      lassign [$iterm getAvgXY] ok x y
      if {$ok} { lappend xs $x; lappend ys $y }
    }
    foreach bterm [$net getBTerms] {
      foreach bpin [$bterm getBPins] {
        set box [$bpin getBBox]
        lappend xs [expr {([$box xMin] + [$box xMax]) / 2.0}]
        lappend ys [expr {([$box yMin] + [$box yMax]) / 2.0}]
      }
    }
    if {[llength $xs] < 2} continue
    set xs [lsort -real $xs]; set ys [lsort -real $ys]
    set total [expr {$total + [lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]}]
  }
  return [expr {$total / [$block getDefUnits]}]
}
set before [total_hpwl]
improve_placement
place_pins -hor_layers metal3 -ver_layers metal2
set after [total_hpwl]
set f [open outputs/hpwl.txt w]
puts $f [format "hpwl_before_um: %.2f" $before]
puts $f [format "hpwl_after_um: %.2f" $after]
close $f
