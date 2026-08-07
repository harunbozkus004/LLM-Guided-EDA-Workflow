# Mistake: only the nets that reach register clock pins (leaf nets) are reported.
set nets {}
foreach pin [all_registers -clock_pins] {
  foreach n [get_nets -of_objects $pin] { lappend nets [get_full_name $n] }
}
report_wire_length -net [lsort -unique $nets] -file outputs/clock_gr_wirelength.txt
