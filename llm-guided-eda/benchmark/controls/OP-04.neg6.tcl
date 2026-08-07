# Miscount: report_check_types without -violators lists only the worst pin of each check,
# so counting its VIOLATED rows gives 1 instead of the number of violating pins.
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
proc count {flag} {
  set f outputs/tmp_[string trimleft $flag -].rpt
  report_check_types $flag > $f
  set fh [open $f r]; set t [read $fh]; close $fh
  return [regexp -all {VIOLATED} $t]
}
estimate_parasitics -placement
set before [list [count -max_slew] [count -max_capacitance] [count -max_fanout]]
repair_design
detailed_placement
estimate_parasitics -placement
set after [list [count -max_slew] [count -max_capacitance] [count -max_fanout]]
set fh [open outputs/drv_summary.txt w]
foreach key {max_slew max_capacitance max_fanout} b $before a $after { puts $fh "$key $b $a" }
close $fh
