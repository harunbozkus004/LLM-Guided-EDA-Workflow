# Alternative: instance padding on every instance instead of the global setting.
set_placement_padding -instances [get_cells *] -left 2 -right 2
detailed_placement
