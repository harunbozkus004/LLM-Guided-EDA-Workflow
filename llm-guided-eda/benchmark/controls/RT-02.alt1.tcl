# Alternative: platform layer settings; the wirelength report auto-detects the global routes.
set_global_routing_layer_adjustment metal2-metal10 0.5
set_routing_layers -signal metal2-metal10 -clock metal6-metal10
global_route -verbose
report_wire_length -net * -file outputs/wl.csv
set total 0
set fh [open outputs/wl.csv r]
while {[gets $fh line] >= 0} {
  if {[regexp {^grt:\s+\S+\s+([0-9.eE+-]+)} $line -> wl]} { set total [expr {$total + $wl}] }
}
close $fh
set out [open outputs/grt_wirelength.txt w]
puts $out "Total global route wirelength: $total um"
close $out
