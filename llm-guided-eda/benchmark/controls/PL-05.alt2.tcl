# Alternative: master-based padding for all masters, no one-site gaps, explicit legality check.
set_placement_padding -masters {*} -right 2 -left 2
detailed_placement -disallow_one_site_gaps
check_placement
