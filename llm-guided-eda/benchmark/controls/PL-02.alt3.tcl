# Alternative: legalization with an explicit displacement limit, then a verbose legality check.
detailed_placement -max_displacement {500 100}
check_placement -verbose
