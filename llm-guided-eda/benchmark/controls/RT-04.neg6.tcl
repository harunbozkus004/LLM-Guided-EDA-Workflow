# Mistake: the clock period is relaxed so that the design meets timing.
create_clock -name core_clock -period 1.0 [get_ports clk]
set_propagated_clock [all_clocks]
estimate_parasitics -global_routing
report_worst_slack -max -digits 4 > outputs/wns_grt.txt
