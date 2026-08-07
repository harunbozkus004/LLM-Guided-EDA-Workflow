# Alternative: rank endpoints with the path API, then report the worst path to each.
# Endpoint names are collected first: PathEnd handles dangle after the next path search.
estimate_parasitics -placement
set sta_report_default_digits 4
set pins {}
foreach pe [find_timing_paths -path_delay max -group_count 10 -endpoint_count 1] {
  lappend pins [get_full_name [[$pe vertex] pin]]
}
set out [open outputs/setup_top10.rpt w]
foreach pin $pins {
  # with_output_to_variable evaluates its body in its own scope: pass a ready-made command.
  with_output_to_variable rpt [list report_checks -path_delay max -to $pin]
  puts $out $rpt
}
close $out
