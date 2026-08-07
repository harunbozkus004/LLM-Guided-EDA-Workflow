# Alternative: flow-style CTS (sink clustering enabled, clock-net repair) plus legalization.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4 \
  -sink_clustering_enable -sink_clustering_max_diameter 100
repair_clock_nets
detailed_placement
