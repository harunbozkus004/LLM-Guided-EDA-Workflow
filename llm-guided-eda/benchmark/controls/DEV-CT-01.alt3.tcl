# Alternative: legalization followed by mirroring optimization and a verbose placement check.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2
detailed_placement
optimize_mirroring
check_placement -verbose
