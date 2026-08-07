# Alternative: flow-style sequence (propagated clock, parasitics, clock-net repair) then legalization.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
set_propagated_clock [all_clocks]
estimate_parasitics -placement
repair_clock_nets
estimate_parasitics -placement
detailed_placement
check_placement
