# Global routing, then the per-net global-route wirelength summed into one total.
global_route
report_wire_length -net * -global_route -file outputs/grt_wirelength_per_net.txt
set total 0.0
set fh [open outputs/grt_wirelength_per_net.txt r]
foreach line [lrange [split [read $fh] "\n"] 1 end] {
  set fields [regexp -all -inline {\S+} $line]
  if {[llength $fields] >= 3} { set total [expr {$total + [lindex $fields 2]}] }
}
close $fh
set out [open outputs/grt_wirelength.txt w]
puts $out [format %.2f $total]
close $out
