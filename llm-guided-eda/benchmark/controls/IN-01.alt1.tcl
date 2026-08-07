# Alternative: walk the block terminals in OpenDB (directions come out upper case, tab separated).
set block [ord::get_db_block]
set fh [open outputs/io_ports.txt w]
foreach bterm [$block getBTerms] {
  puts $fh "[$bterm getName]\t[$bterm getIoType]"
}
close $fh
