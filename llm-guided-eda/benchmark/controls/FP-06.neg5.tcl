# Wrong pattern: endcaps plus taps every 40 um in every row at the same x (columns, no checkerboard stagger).
place_endcaps -endcap_vertical TAPCELL_X1
set block [ord::get_db_block]
set master [[ord::get_db] findMaster TAPCELL_X1]
set w [$master getWidth]
set k 0
foreach row [$block getRows] {
  set bb [$row getBBox]
  set y [$bb yMin]
  set orient [$row getOrient]
  for {set x [expr {[$bb xMin] + 40000}]} {$x + $w <= [$bb xMax] - 2 * $w} {incr x 79800} {
    set inst [odb::dbInst_create $block $master "TAP_COL_$k"]
    incr k
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus LOCKED
  }
}
