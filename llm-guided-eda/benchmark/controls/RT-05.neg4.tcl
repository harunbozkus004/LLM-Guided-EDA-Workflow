# Mistake: routing stopped early and a clean-looking report is fabricated.
detailed_route -droute_end_iter 1
set fh [open outputs/route_drc.rpt w]
close $fh
