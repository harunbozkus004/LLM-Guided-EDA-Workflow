# Alternative: explicit waveform, value copied from the 4-digit worst-slack report.
create_clock -name core_clock -period 0.40 -waveform {0 0.20} [get_ports clk]
with_output_to_variable a { report_worst_slack -max -digits 4 }
regexp {worst slack\s+(\S+)} $a -> wss
set f [open outputs/period_0p40.txt w]
puts $f "worst_setup_slack $wss"
puts $f "setup_violating_endpoints [sta::endpoint_violation_count max]"
close $f
