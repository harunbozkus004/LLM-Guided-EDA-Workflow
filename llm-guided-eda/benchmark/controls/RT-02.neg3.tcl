# Mistake: the report is produced without running global routing first.
report_wire_length -net * -global_route -file outputs/wl.txt
set total 0.0
set fh [open outputs/wl.txt r]
foreach line [lrange [split [read $fh] "\n"] 1 end] {
  set fields [regexp -all -inline {\S+} $line]
  if {[llength $fields] >= 3} { set total [expr {$total + [lindex $fields 2]}] }
}
close $fh
set out [open outputs/grt_wirelength.txt w]
puts $out $total
close $out
