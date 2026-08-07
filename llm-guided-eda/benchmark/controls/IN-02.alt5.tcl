# Alternative: hand-written netlist from the STA network. Every name is an escaped identifier, port bits
# are scalar ports whose nets carry the same name, and pins on single-pin nets are left unconnected.
proc vname {name} { return "\\$name " }
set fh [open outputs/gcd_netlist.v w]
set ports [get_ports *]
puts $fh "module gcd ([join [lmap p $ports {vname [get_full_name $p]}] {, }]);"
foreach p $ports { puts $fh "  [get_property $p direction] [vname [get_full_name $p]];" }
foreach net [get_nets *] {
  set name [get_full_name $net]
  if {$name ni {VDD VSS} && [llength [get_ports -quiet $name]] == 0} { puts $fh "  wire [vname $name];" }
}
foreach cell [get_cells *] {
  set ref [get_property $cell ref_name]
  if {[string match TAPCELL* $ref]} { continue }
  set conns {}
  foreach pin [get_pins -of_objects $cell] {
    set net [get_nets -quiet -of_objects $pin]
    set n [expr {[llength $net] ? [get_full_name $net] : ""}]
    if {$n ne "" && [llength [get_pins -quiet -of_objects $net]] + [llength [get_ports -quiet -of_objects $net]] < 2} {
      set n ""
    }
    lappend conns ".[get_property $pin lib_pin_name]([expr {$n eq {} ? {} : [vname $n]}])"
  }
  puts $fh "  $ref [vname [get_full_name $cell]]([join $conns {, }]);"
}
puts $fh "endmodule"
close $fh
