# Alternative: root buffer from the buffer list, flow-style clock-net repair, then legalization.
clock_tree_synthesis -buf_list BUF_X2 -sink_clustering_enable
repair_clock_nets
detailed_placement
