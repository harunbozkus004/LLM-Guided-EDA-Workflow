# Mistake: global routing re-run (default settings) instead of using the existing routes.
global_route
estimate_parasitics -global_routing
report_worst_slack -max -digits 4 > outputs/wns_grt.txt
