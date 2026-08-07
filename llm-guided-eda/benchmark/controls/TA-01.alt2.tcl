# Alternative: find the 3 worst hold endpoints first, then report the worst path to each one.
# Endpoint names are collected before reporting: PathEnd handles are invalidated by the next
# path search (report_checks), so they must not be used inside the reporting loop.
set sta_report_default_digits 4
set pins {}
foreach pe [find_timing_paths -path_delay min -group_count 3 -endpoint_count 1] {
  lappend pins [get_full_name [[$pe vertex] pin]]
}
report_checks -path_delay min -to [lindex $pins 0] > outputs/hold_paths.rpt
foreach pin [lrange $pins 1 end] {
  report_checks -path_delay min -to $pin >> outputs/hold_paths.rpt
}
