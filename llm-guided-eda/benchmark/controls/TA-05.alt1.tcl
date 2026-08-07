# Alternative: take the values from the standard WNS/TNS reports and reformat them.
estimate_parasitics -global_routing
with_output_to_variable wns_rpt { report_wns -digits 6 }
with_output_to_variable tns_rpt { report_tns -digits 6 }
regexp {wns\s+(\S+)} $wns_rpt -> wns
regexp {tns\s+(\S+)} $tns_rpt -> tns
set f [open outputs/wns_tns.txt w]
puts $f [format "WNS=%.4f TNS=%.4f" $wns $tns]
close $f
