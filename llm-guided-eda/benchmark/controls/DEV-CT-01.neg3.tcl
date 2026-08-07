# Wrong order: legalization run before CTS, so the new clock buffers are never legalized.
detailed_placement
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
