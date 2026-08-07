# Version pitfall: -tree_buf is ignored and -root_buf sets every H-tree buffer (all BUF_X8).
clock_tree_synthesis -root_buf BUF_X8 -tree_buf BUF_X2 -buf_list BUF_X2
detailed_placement
