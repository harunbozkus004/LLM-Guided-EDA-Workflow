# Stricter design rules for the whole design (time in ns, capacitance in fF).
set_max_transition 0.05 [current_design]
set_max_capacitance 10 [current_design]
set_max_fanout 10 [current_design]

# Number of violating pins listed by report_check_types for one rule.
proc count_violators {flag tag} {
  set rpt outputs/drv_${tag}[string map {- _} $flag].rpt
  report_check_types $flag -violators > $rpt
  set fh [open $rpt r]
  set n [regexp -all -line {\(VIOLATED\)\s*$} [read $fh]]
  close $fh
  return $n
}
proc drv_counts {tag} {
  return [list [count_violators -max_slew $tag] [count_violators -max_capacitance $tag] \
            [count_violators -max_fanout $tag]]
}

estimate_parasitics -placement
set before [drv_counts before]
repair_design
detailed_placement
# Parasitics must describe the legalized placement before counting again.
estimate_parasitics -placement
set after [drv_counts after]

set fh [open outputs/drv_summary.txt w]
foreach key {max_slew max_capacitance max_fanout} b $before a $after {
  puts $fh "$key $b $a"
}
close $fh
