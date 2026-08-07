# Wrong order: legalized before upsizing the root, so the wider BUF_X8 overlaps its neighbours.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
detailed_placement
replace_cell clkbuf_0_clk BUF_X8
