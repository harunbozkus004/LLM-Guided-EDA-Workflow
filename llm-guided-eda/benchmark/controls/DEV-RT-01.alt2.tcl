# Alternative: report_wire_length without route-type flags (it reports both kinds); sum the drt lines.
detailed_route -bottom_routing_layer metal2 -top_routing_layer metal10 -output_drc outputs/drc.rpt
report_wire_length -net * -file outputs/wl.csv
set total 0.0
set fh [open outputs/wl.csv r]
while {[gets $fh line] >= 0} {
  if {[regexp {^drt:\s+\S+\s+([0-9.eE+-]+)} $line -> wl]} { set total [expr {$total + $wl}] }
}
close $fh
set out [open outputs/dr_wirelength.txt w]
puts $out [format "%.2f" $total]
close $out
