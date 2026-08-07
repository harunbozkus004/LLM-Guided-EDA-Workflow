# Wrong attribute: the signal type (SIGNAL/CLOCK) is written instead of the direction.
set block [ord::get_db_block]
set fh [open outputs/io_ports.txt w]
foreach bterm [$block getBTerms] {
  puts $fh "[$bterm getName] [$bterm getSigType]"
}
close $fh
