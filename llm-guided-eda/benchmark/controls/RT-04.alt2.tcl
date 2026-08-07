# Alternative: worst negative slack report (the design has negative setup slack).
estimate_parasitics -global_routing
report_wns -digits 4 > outputs/wns_grt.txt
