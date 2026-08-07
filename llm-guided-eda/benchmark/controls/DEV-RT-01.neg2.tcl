# Mistake: the global-route wirelength is reported instead of the detailed-route wirelength.
detailed_route -bottom_routing_layer metal2 -top_routing_layer metal10
grt::have_routes
report_wire_length -net * -global_route -file outputs/wl.csv
set total 0.0
set fh [open outputs/wl.csv r]
foreach line [lrange [split [read $fh] "\n"] 1 end] {
  set fields [regexp -all -inline {\S+} $line]
  if {[llength $fields] >= 3} { set total [expr {$total + [lindex $fields 2]}] }
}
close $fh
set fh [open outputs/dr_wirelength.txt w]
puts $fh $total
close $fh
