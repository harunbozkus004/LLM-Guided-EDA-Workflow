# Alternative: ports selected with STA direction filters, aligned columns, one pass per direction.
set fh [open outputs/io_ports.txt w]
foreach dir {input output} {
  foreach port [get_ports -filter "direction==$dir" *] {
    puts $fh [format "%-14s %s" [get_full_name $port] $dir]
  }
}
close $fh
