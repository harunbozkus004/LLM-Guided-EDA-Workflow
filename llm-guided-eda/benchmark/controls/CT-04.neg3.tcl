# Wrong object: a leaf buffer is upsized instead of the root buffer.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
replace_cell clkbuf_2_0__f_clk BUF_X8
detailed_placement
