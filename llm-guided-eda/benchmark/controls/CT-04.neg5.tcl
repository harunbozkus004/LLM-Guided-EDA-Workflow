# Version pitfall: the sink-clustering buffer does not set the tree buffers either; the tree is all BUF_X8.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X2 -sink_clustering_enable -sink_clustering_buffer BUF_X2
detailed_placement
