# Alternative: instance padding on the flip-flops selected through STA.
set_placement_padding -instances [get_cells -filter "ref_name == DFF_X1" *] -left 3 -right 3
detailed_placement
