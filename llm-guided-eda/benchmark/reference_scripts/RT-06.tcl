# Clock nets are marked CLOCK in the database. Without -global_route/-detailed_route the
# wirelength report first rebuilds the global routes from the guides stored in the database.
set nets {}
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] == "CLOCK"} { lappend nets [$net getName] }
}
report_wire_length -net $nets -file outputs/clock_gr_wirelength.csv
set in [open outputs/clock_gr_wirelength.csv r]
set out [open outputs/clock_gr_wirelength.txt w]
while {[gets $in line] >= 0} {
  set fields [regexp -all -inline {\S+} $line]
  if {[lindex $fields 0] == "grt:"} { puts $out "[lindex $fields 1] [lindex $fields 2]" }
}
close $in
close $out
