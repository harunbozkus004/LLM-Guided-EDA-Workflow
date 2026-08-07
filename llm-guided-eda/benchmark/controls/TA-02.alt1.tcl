# Alternative: paths through the port pin, expanded format with extra columns.
report_checks -through [get_ports reset] -path_delay max -format full_clock_expanded \
  -fields {slew cap net} -digits 4 > outputs/reset_setup_path.rpt
