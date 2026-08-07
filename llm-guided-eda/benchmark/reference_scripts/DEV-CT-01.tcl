# Clock tree synthesis with BUF_X2, then legalization of the clock buffers.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
detailed_placement
