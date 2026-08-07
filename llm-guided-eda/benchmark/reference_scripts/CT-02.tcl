# Clock tree synthesis with BUF_X8 everywhere, then the CTS summary metrics.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
# This build only accepts the output file through -out_file (the README
# example `report_cts "file.txt"` and `report_cts > file` are rejected).
report_cts -out_file outputs/ct02_cts_summary.txt
