# Alternative: clock nets selected with the pattern clk*, a header line and 2-decimal values.
grt::have_routes
report_wire_length -net clk* -global_route -file outputs/raw.csv
set in [open outputs/raw.csv r]
set out [open outputs/clock_gr_wirelength.txt w]
puts $out "net wirelength_um"
while {[gets $in line] >= 0} {
  set f [regexp -all -inline {\S+} $line]
  if {[lindex $f 0] == "grt:"} { puts $out [list "[lindex $f 1]" [format %.2f [lindex $f 2]]] }
}
close $in
close $out
