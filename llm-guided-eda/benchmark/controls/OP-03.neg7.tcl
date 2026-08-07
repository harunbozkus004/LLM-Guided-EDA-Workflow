# Clock tree modified: clock-tree buffers upsized to speed up the clock, then setup repair.
foreach inst [[ord::get_db_block] getInsts] {
  if {[string match clkbuf* [$inst getName]]} { $inst swapMaster [[ord::get_db] findMaster BUF_X8] }
}
estimate_parasitics -placement
repair_timing -setup -repair_tns 100
detailed_placement
