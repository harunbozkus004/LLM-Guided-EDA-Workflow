# Alternative: report one net at a time with the verbose per-layer breakdown and sum the totals.
global_route -allow_congestion
set total 0.0
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] in {POWER GROUND} || [$net isSpecial]} { continue }
  if {![llength [$net getGuides]]} { continue }
  report_wire_length -net [$net getName] -global_route -verbose -file outputs/one.csv
  set fh [open outputs/one.csv r]
  set lines [split [read $fh] "\n"]
  close $fh
  set f [regexp -all -inline {\S+} [lindex $lines 1]]
  set total [expr {$total + [lindex $f 2]}]
}
set out [open outputs/grt_wirelength.txt w]
puts $out "[format %.1f $total] um"
close $out
