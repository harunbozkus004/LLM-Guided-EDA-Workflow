# Alternative: capture an expanded-format report in a variable and write it with Tcl file I/O.
with_output_to_variable rpt {
  report_checks -path_delay min -group_count 3 -format full_clock_expanded \
    -fields {slew cap input_pin} -digits 4
}
set f [open outputs/hold_paths.rpt w]
puts $f $rpt
close $f
