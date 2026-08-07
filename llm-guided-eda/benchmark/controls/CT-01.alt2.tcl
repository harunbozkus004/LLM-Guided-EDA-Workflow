# Alternative: root buffer taken from the buffer list, explicit clock net, extra reporting.
clock_tree_synthesis -buf_list {BUF_X4} -clk_nets clk
set_propagated_clock [all_clocks]
report_cts
report_clock_skew
