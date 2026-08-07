# Alternative: values copied from the standard reports printed with 4 digits.
estimate_parasitics -global_routing
with_output_to_variable w { report_wns -digits 4 }
with_output_to_variable t { report_tns -digits 4 }
set f [open outputs/wns_tns.txt w]
puts $f "WNS=[lindex $w 1] TNS=[lindex $t 1]"
close $f
