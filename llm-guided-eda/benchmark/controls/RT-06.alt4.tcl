# Alternative: STA net patterns (clk, clknet_*), verbose report, lines written as "<net>: <wl> um".
grt::have_routes
set names [list clk]
foreach n [get_nets clknet_*] { lappend names [get_full_name $n] }
report_wire_length -net $names -global_route -verbose -file outputs/raw.csv
set in [open outputs/raw.csv r]
set out [open outputs/clock_gr_wirelength.txt w]
while {[gets $in line] >= 0} {
  set f [regexp -all -inline {\S+} $line]
  if {[lindex $f 0] == "grt:"} { puts $out "[lindex $f 1]: [lindex $f 2] um" }
}
close $in
close $out
