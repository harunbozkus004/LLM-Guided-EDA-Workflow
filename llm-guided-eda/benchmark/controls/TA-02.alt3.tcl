# Alternative: expanded format captured in a variable and written with Tcl file I/O.
with_output_to_variable rpt {
  report_checks -from [get_ports {reset}] -path_delay max -format full_clock_expanded -digits 4
}
set f [open outputs/reset_setup_path.rpt w]
puts $f $rpt
close $f
