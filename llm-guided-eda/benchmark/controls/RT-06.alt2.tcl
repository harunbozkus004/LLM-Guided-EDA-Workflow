# Alternative: rebuild the routes explicitly and report one net at a time.
grt::have_routes
set out [open outputs/clock_gr_wirelength.txt w]
foreach net [[ord::get_db_block] getNets] {
  if {[$net getSigType] != "CLOCK"} { continue }
  report_wire_length -net [$net getName] -global_route -file outputs/one_net.csv
  set in [open outputs/one_net.csv r]
  set lines [split [read $in] "\n"]
  close $in
  set fields [regexp -all -inline {\S+} [lindex $lines 1]]
  puts $out "[$net getName] [lindex $fields 2]"
}
close $out
