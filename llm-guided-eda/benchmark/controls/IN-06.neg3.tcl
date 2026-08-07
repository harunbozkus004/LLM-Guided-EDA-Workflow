# Wrong object: lists the clock nets instead of the driving cell instances.
set types [dict create]
foreach reg [all_registers -cells] { dict incr types [get_property $reg ref_name] }
set nets [dict create]
foreach ck_pin [all_registers -clock_pins] { dict incr nets [get_full_name [get_nets -of_objects $ck_pin]] }
set total 0
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref $n"; incr total $n }
puts $fh "total $total"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
dict for {net n} $nets { puts $fh "$net $n" }
close $fh
