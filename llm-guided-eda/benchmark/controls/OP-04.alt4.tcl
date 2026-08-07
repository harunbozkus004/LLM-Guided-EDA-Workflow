# Alternative: counts parsed from report_check_types -violators (one report per check,
# "(VIOLATED)" rows), repair, legalize, recount; report written line by line.
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]
proc count {flag} {
  set f outputs/tmp_[string trimleft $flag -].rpt
  report_check_types $flag -violators -digits 4 > $f
  set fh [open $f r]; set n 0
  while {[gets $fh line] >= 0} { if {[string match "*VIOLATED*" $line]} { incr n } }
  close $fh
  return $n
}
estimate_parasitics -placement
array set B {}; array set A {}
foreach c {max_slew max_capacitance max_fanout} { set B($c) [count -$c] }
repair_design
detailed_placement
estimate_parasitics -placement
foreach c {max_slew max_capacitance max_fanout} { set A($c) [count -$c] }
set fh [open outputs/drv_summary.txt w]
foreach c {max_slew max_capacitance max_fanout} { puts $fh "$c $B($c) $A($c)" }
close $fh
