# Fabricated from the RTL port list: bus ports are not expanded bit by bit.
set fh [open outputs/io_ports.txt w]
foreach {name dir} {clk input reset input req_val input req_rdy output req_msg input
                    resp_val output resp_rdy input resp_msg output} {
  puts $fh "$name $dir"
}
close $fh
