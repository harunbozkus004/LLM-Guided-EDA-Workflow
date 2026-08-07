# Wrong buffer cell (BUF_X4, the platform default) with a correct report.
clock_tree_synthesis -root_buf BUF_X4 -buf_list BUF_X4
report_cts -out_file outputs/ct02_cts_summary.txt
