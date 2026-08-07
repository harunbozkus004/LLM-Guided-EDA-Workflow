# Alternative: inputs and outputs collected separately and sorted, plus a harmless timing report.
set lines {}
foreach port [all_inputs] { lappend lines [list [get_full_name $port] input] }
foreach port [all_outputs] { lappend lines [list [get_full_name $port] output] }
set fh [open outputs/io_ports.txt w]
foreach line [lsort -dictionary -index 0 $lines] { puts $fh $line }
close $fh
report_checks -path_delay max -group_count 1
