# Alternative: platform clock layers, congestion report, guides from the router plus a timing check.
set_routing_layers -clock metal6-metal10 -signal metal2-metal10
global_route -guide_file outputs/gcd.guide -congestion_report_file outputs/congestion.rpt -verbose
estimate_parasitics -global_routing
report_worst_slack -max
