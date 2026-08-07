# Mistake: estimated (global-route) parasitics instead of RC extraction.
estimate_parasitics -global_routing
write_spef outputs/gcd.spef
report_worst_slack -max -digits 4 > outputs/wns_rcx.txt
