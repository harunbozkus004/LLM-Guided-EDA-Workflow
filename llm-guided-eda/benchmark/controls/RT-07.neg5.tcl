# Mistake: write_spef without a prior extraction (writes nothing), then timing on whatever is there.
write_spef outputs/gcd.spef
report_worst_slack -max -digits 4 > outputs/wns_rcx.txt
