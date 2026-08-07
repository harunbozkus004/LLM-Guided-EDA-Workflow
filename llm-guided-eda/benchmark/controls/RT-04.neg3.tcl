# Mistake: hold slack reported instead of setup slack.
estimate_parasitics -global_routing
report_worst_slack -min -digits 4 > outputs/wns_grt.txt
