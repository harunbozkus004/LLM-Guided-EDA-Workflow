# Mistake: default report precision (2 decimals) instead of 4.
estimate_parasitics -global_routing
report_worst_slack -max > outputs/wns_grt.txt
