# Alternative: sink clustering with level balancing (deeper tree, all buffers still BUF_X4).
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4 -sink_clustering_enable -balance_levels
