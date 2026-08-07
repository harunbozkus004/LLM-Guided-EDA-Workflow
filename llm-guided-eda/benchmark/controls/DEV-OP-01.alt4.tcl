# Alternative: limit set on every input port and the design, repair, legalize, report fanout per net.
set_max_fanout 10 [current_design]
set_max_fanout 10 [all_inputs]
estimate_parasitics -placement
repair_design -max_utilization 70
detailed_placement
report_net -connections req_rdy
