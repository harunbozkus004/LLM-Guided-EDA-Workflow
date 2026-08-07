# Alternative: full flow-style CTS stage (propagated clock, parasitics, clock-net repair,
# legalization and setup repair); the clock-tree buffers stay BUF_X4.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
set_propagated_clock [all_clocks]
estimate_parasitics -placement
repair_clock_nets
estimate_parasitics -placement
detailed_placement
repair_timing
detailed_placement
report_cts
