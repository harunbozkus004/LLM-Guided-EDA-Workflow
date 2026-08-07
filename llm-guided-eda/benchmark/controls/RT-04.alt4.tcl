# Alternative: the worst setup path's slack taken from the timing-path object.
estimate_parasitics -global_routing
set path [find_timing_paths -path_delay max -group_count 1]
set slack [get_property $path slack]
set fh [open outputs/wns_grt.txt w]
puts $fh [format %.4f $slack]
close $fh
