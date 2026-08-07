# Transitive instead of direct: the clock path of every flip-flop is traced back to the clock port and
# every buffer on it is counted, so the root buffer is listed with all 35 flip-flops.
# (all_fanin does not exist in this build, hence the manual trace.)
set types [dict create]
foreach reg [all_registers -cells] { dict incr types [get_property $reg ref_name] }
set drivers [dict create]
foreach ck [all_registers -clock_pins] {
  set pin $ck
  while 1 {
    set drv [get_pins -quiet -of_objects [get_nets -of_objects $pin] -filter "direction==output"]
    if {[llength $drv] == 0} { break }
    set cell [get_cells -of_objects $drv]
    dict incr drivers [get_full_name $cell]
    set pin [get_pins -of_objects $cell -filter "direction==input"]
  }
}
set fh [open outputs/flop_types.txt w]
dict for {ref n} $types { puts $fh "$ref $n" }
puts $fh "total [llength [all_registers -cells]]"
close $fh
set fh [open outputs/flop_clock_drivers.txt w]
dict for {inst n} $drivers { puts $fh "$inst $n" }
close $fh
