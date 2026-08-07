# Clock tree modified: hold "fixed" by downsizing every clock-tree buffer (delays the capture clock).
foreach inst [[ord::get_db_block] getInsts] {
  if {[string match clkbuf* [$inst getName]]} { $inst swapMaster [[ord::get_db] findMaster BUF_X1] }
}
estimate_parasitics -placement
repair_timing -hold -hold_margin 0.08
detailed_placement
