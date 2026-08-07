# Alternative: redirect the slack report to the file.
estimate_parasitics -global_routing
report_worst_slack -max -digits 4 > outputs/wns_grt.txt
