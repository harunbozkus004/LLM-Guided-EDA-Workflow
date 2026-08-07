# Hand-written placer instead of global placement: packs the cells row by row in netlist order.
set block [ord::get_db_block]
set rows [$block getRows]
set ri 0
set row [lindex $rows $ri]
set x [[$row getBBox] xMin]
foreach inst [$block getInsts] {
  set m [$inst getMaster]
  if {[$m getType] ne "CORE"} continue
  set w [$m getWidth]
  while {$x + $w > [[$row getBBox] xMax]} {
    incr ri
    set row [lindex $rows $ri]
    set x [[$row getBBox] xMin]
  }
  $inst setOrient [$row getOrient]
  $inst setLocation $x [[$row getBBox] yMin]
  $inst setPlacementStatus PLACED
  set x [expr {$x + $w}]
}
