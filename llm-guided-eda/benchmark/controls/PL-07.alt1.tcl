# Greedy mirroring about the Y axis with odb: keep a flip only if it shortens the cell's nets.
proc net_hpwl {net} {
  set xs {}; set ys {}
  foreach it [$net getITerms] {
    set a [$it getAvgXY]
    if {[lindex $a 0]} { lappend xs [lindex $a 1]; lappend ys [lindex $a 2] }
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
array set mirror_y {R0 MY MY R0 MX R180 R180 MX}
set nflip 0
foreach inst [[ord::get_db_block] getInsts] {
  if {[[$inst getMaster] getType] ne "CORE"} continue
  set before [cell_cost $inst]
  lassign [$inst getLocation] x y
  set o [$inst getOrient]
  # setOrient keeps the transform origin, so restore the lower-left corner afterwards
  $inst setOrient $mirror_y($o)
  $inst setLocation $x $y
  if {[cell_cost $inst] < $before} {
    incr nflip
  } else {
    $inst setOrient $o
    $inst setLocation $x $y
  }
}
puts "flipped $nflip cells"
