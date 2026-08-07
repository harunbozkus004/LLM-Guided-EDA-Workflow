# Wrong axis: greedy mirroring about the X axis (R0<->MX, MY<->R180), which breaks the row orientation.
proc net_hpwl {net} {
  set xs {}; set ys {}
  foreach it [$net getITerms] {
    lassign [$it getAvgXY] ok x y
    if {$ok} { lappend xs $x; lappend ys $y }
  }
  foreach bt [$net getBTerms] {
    foreach bp [$bt getBPins] {
      set b [$bp getBBox]
      lappend xs [expr {([$b xMin] + [$b xMax]) / 2.0}]
      lappend ys [expr {([$b yMin] + [$b yMax]) / 2.0}]
    }
  }
  if {[llength $xs] < 2} { return 0.0 }
  set xs [lsort -real $xs]; set ys [lsort -real $ys]
  return [expr {[lindex $xs end] - [lindex $xs 0] + [lindex $ys end] - [lindex $ys 0]}]
}
proc cell_cost {inst} {
  set c 0.0
  foreach it [$inst getITerms] {
    set n [$it getNet]
    if {$n eq "NULL" || [$n getSigType] in {POWER GROUND}} continue
    set c [expr {$c + [net_hpwl $n]}]
  }
  return $c
}
array set mirror_x {R0 MX MX R0 MY R180 R180 MY}
foreach inst [[ord::get_db_block] getInsts] {
  if {[[$inst getMaster] getType] ne "CORE"} continue
  set before [cell_cost $inst]
  lassign [$inst getLocation] x y
  set o [$inst getOrient]
  $inst setOrient $mirror_x($o)
  $inst setLocation $x $y
  if {[cell_cost $inst] >= $before} {
    $inst setOrient $o
    $inst setLocation $x $y
  }
}
