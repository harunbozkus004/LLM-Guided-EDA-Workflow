# Wrong place: the report is written to the working directory instead of outputs/.
set fh [open io_ports.txt w]
foreach port [get_ports *] {
  puts $fh "[get_full_name $port] [get_property $port direction]"
}
close $fh
