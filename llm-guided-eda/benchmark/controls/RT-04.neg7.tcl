# Mistake: clocks switched back to ideal before reporting.
estimate_parasitics -global_routing
unset_propagated_clock [all_clocks]
report_worst_slack -max -digits 4 > outputs/wns_grt.txt
