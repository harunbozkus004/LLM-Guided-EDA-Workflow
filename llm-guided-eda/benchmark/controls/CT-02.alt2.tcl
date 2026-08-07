# Alternative: root buffer defaults to the first buffer of the list; legalized afterwards.
clock_tree_synthesis -buf_list BUF_X8
detailed_placement
report_cts -out_file outputs/ct02_cts_summary.txt
