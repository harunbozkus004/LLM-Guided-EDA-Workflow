# Fake placement: every cell gets a placed status at the core centre (all stacked on top of each other).
set block [ord::get_db_block]
set core [$block getCoreArea]
set cx [expr {([$core xMin] + [$core xMax]) / 2}]
set cy [expr {([$core yMin] + [$core yMax]) / 2}]
foreach inst [$block getInsts] {
  if {[[$inst getMaster] getType] ne "CORE"} continue
  $inst setLocation $cx $cy
  $inst setPlacementStatus PLACED
}
