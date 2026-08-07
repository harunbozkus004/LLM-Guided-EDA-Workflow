# Alternative: compute WNS/TNS from the worst path of every endpoint.
estimate_parasitics -global_routing
set wns 1e30
set tns 0.0
foreach pe [find_timing_paths -path_delay max -group_count 100000 -endpoint_count 1] {
  set s [sta::time_sta_ui [$pe slack]]
  if {$s < $wns} { set wns $s }
  if {$s < 0} { set tns [expr {$tns + $s}] }
}
set f [open outputs/wns_tns.txt w]
puts $f "WNS=[format %.4f $wns] TNS=[format %.4f $tns]"
close $f
