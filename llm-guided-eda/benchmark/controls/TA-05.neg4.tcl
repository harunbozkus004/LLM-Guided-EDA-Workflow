# Precision mistake: values copied from the reports at their default 2 digits.
estimate_parasitics -global_routing
with_output_to_variable w { report_wns }
with_output_to_variable t { report_tns }
set f [open outputs/wns_tns.txt w]
puts $f "WNS=[lindex $w 1] TNS=[lindex $t 1]"
close $f
