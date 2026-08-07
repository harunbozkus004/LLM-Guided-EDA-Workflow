# Wrong source: counts cell types in the synthesized netlist file instead of the current design.
set fh [open design/gcd.v r]
set text [read $fh]
close $fh
set usage [dict create]
foreach {all ref} [regexp -all -inline -line {^\s*([A-Z][A-Z0-9_]*)\s+\S+\s*\($} $text] {
  dict incr usage $ref
}
set total 0
set fh [open outputs/cell_usage.txt w]
dict for {ref n} $usage { puts $fh "$ref $n"; incr total $n }
puts $fh "total $total"
close $fh
