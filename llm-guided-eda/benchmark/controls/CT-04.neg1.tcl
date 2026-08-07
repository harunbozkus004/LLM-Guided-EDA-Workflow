# Version pitfall: -root_buf also sets the tree buffers, so the tree is all BUF_X8.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X2
detailed_placement
