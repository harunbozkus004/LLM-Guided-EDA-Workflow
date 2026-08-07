# Wrong: the clock input is filtered out (the SDC idiom for non-clock inputs) before listing the inputs.
set data_inputs [lsearch -inline -all -not -exact [all_inputs] [get_ports clk]]
set fh [open outputs/io_ports.txt w]
foreach port $data_inputs { puts $fh "[get_full_name $port] input" }
foreach port [all_outputs] { puts $fh "[get_full_name $port] output" }
close $fh
