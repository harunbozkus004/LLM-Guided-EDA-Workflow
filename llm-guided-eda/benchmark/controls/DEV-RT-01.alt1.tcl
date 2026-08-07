# Alternative: explicit pin access, then the wirelength report summed.
pin_access -bottom_routing_layer metal2 -top_routing_layer metal10
detailed_route -no_pin_access -bottom_routing_layer metal2 -top_routing_layer metal10 -verbose 0
report_wire_length -net * -detailed_route -file outputs/dr_wl.csv
set total 0.0
set fh [open outputs/dr_wl.csv r]
foreach line [lrange [split [read $fh] "\n"] 1 end] {
  set fields [regexp -all -inline {\S+} $line]
  if {[llength $fields] >= 3} { set total [expr {$total + [lindex $fields 2]}] }
}
close $fh
set fh [open outputs/dr_wirelength.txt w]
puts $fh "$total um"
close $fh
