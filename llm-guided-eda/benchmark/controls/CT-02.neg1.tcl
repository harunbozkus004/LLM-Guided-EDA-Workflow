# Summary written before the clock tree exists (all zeros).
report_cts -out_file outputs/ct02_cts_summary.txt
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
