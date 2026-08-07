# Alternative: coupling capacitance kept (no coupling threshold), value written with a label.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules -coupling_threshold 0
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
set fh [open outputs/wns_rcx.txt w]
puts $fh "Worst setup slack: [format %.4f [sta::worst_slack -max]] ns"
close $fh
