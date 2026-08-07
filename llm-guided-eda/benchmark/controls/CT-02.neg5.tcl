# report_cts prints through the logger, so capturing it in a variable yields an empty summary.
clock_tree_synthesis -root_buf BUF_X8 -buf_list BUF_X8
with_output_to_variable rpt { report_cts }
set f [open outputs/ct02_cts_summary.txt w]
puts -nonewline $f $rpt
close $f
