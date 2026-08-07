# Destructive clean-up: remove_buffers after CTS also deletes the clock-tree buffers,
# so the registers are driven directly by the clk port again.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
remove_buffers
