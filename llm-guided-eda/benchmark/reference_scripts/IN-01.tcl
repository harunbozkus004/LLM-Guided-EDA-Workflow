# List every top-level port bit with its direction.
set fh [open outputs/io_ports.txt w]
foreach port [get_ports *] {
  puts $fh "[get_full_name $port] [get_property $port direction]"
}
close $fh
