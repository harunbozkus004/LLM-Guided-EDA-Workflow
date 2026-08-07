# Mistake: clock nets are left out of the total.
global_route
set clock_nets {}
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] == "CLOCK"} { lappend clock_nets [$net getName] }
}
report_wire_length -net * -global_route -file outputs/wl.txt
set total 0.0
set fh [open outputs/wl.txt r]
foreach line [lrange [split [read $fh] "\n"] 1 end] {
  set fields [regexp -all -inline {\S+} $line]
  if {[llength $fields] >= 3 && [lindex $fields 1] ni $clock_nets} { set total [expr {$total + [lindex $fields 2]}] }
}
close $fh
set out [open outputs/grt_wirelength.txt w]
puts $out $total
close $out
