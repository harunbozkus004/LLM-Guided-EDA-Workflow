# Mistake: placement-based parasitic estimate instead of the global routing.
estimate_parasitics -placement
report_worst_slack -max -digits 4 > outputs/wns_grt.txt
