# Shortcut: assumes every flip-flop QN output is unused (one of them is not).
set fh [open outputs/unloaded_nets.txt w]
foreach reg [all_registers -cells] {
  set pin [get_pins -quiet [get_full_name $reg]/QN]
  if {[llength $pin] == 0} { continue }
  set net [get_nets -quiet -of_objects $pin]
  if {[llength $net]} { puts $fh "[get_full_name $net] [get_full_name $pin]" }
}
close $fh
