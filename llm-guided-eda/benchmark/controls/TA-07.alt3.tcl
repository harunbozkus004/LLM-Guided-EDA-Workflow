# Alternative: no process corner, values parsed from 4-digit standard reports.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
with_output_to_variable a { report_worst_slack -max -digits 4 }
with_output_to_variable b { report_tns -digits 4 }
with_output_to_variable c { report_worst_slack -min -digits 4 }
regexp {worst slack\s+(\S+)} $a -> wss
regexp {tns\s+(\S+)} $b -> tns
regexp {worst slack\s+(\S+)} $c -> whs
set f [open outputs/signoff_summary.txt w]
puts $f "worst_setup_slack $wss"
puts $f "total_negative_setup_slack $tns"
puts $f "worst_hold_slack $whs"
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
