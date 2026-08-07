# Alternative: bounded-displacement legalization plus mirroring optimization.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
replace_cell clkbuf_0_clk BUF_X8
detailed_placement -max_displacement 20
optimize_mirroring
check_placement
