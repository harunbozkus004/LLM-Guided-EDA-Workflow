# Alternative: global report precision instead of a per-command option, explicit counts.
set sta_report_default_digits 4
report_checks -from reset -group_count 1 -endpoint_count 1 > outputs/reset_setup_path.rpt
