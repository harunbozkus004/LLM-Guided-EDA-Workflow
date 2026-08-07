# RC extraction with the platform rules; STA only sees the parasitics once the SPEF is read.
extract_parasitics -ext_model_file platform/Nangate45.rcx_rules
write_spef outputs/gcd.spef
read_spef outputs/gcd.spef
set fh [open outputs/wns_rcx.txt w]
puts $fh [format %.4f [sta::worst_slack -max]]
close $fh
