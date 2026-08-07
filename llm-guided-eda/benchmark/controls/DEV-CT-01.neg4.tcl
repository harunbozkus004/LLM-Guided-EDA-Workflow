# Buffer list contains BUF_X2 but starts with BUF_X4: without -root_buf the first cell is used
# for every buffer, so the tree is all BUF_X4.
clock_tree_synthesis -buf_list {BUF_X4 BUF_X2}
detailed_placement
