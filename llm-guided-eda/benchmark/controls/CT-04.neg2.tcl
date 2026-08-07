# Correct buffers but the placement is never legalized.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
replace_cell clkbuf_0_clk BUF_X8
