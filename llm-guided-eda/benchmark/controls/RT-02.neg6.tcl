# Mistake: total reported in millimeters instead of micrometers.
global_route
report_wire_length -net * -global_route -file outputs/per_net.txt
set total 0.0
set fh [open outputs/per_net.txt r]
foreach line [lrange [split [read $fh] "\n"] 1 end] {
  set f [regexp -all -inline {\S+} $line]
  if {[llength $f] >= 3} { set total [expr {$total + [lindex $f 2]}] }
}
close $fh
set out [open outputs/grt_wirelength.txt w]
puts $out [format %.3f [expr {$total / 1000.0}]]
close $out
