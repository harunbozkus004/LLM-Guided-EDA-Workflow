# Mistake: the per-net report itself is written to the requested file instead of the total.
global_route
report_wire_length -net * -global_route -file outputs/grt_wirelength.txt
