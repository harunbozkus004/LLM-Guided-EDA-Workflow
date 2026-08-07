# Mistake: the wiring is stripped before writing (e.g. to "clean up" the DEF).
foreach net [[ord::get_db_block] getNets] {
  if {[$net getWire] != "NULL"} { odb::dbWire_destroy [$net getWire] }
}
write_def outputs/gcd_route.def
