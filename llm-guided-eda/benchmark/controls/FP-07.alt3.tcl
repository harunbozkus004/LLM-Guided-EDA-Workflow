# Alternative: configuration file, verbose build, then an explicit reconnect and a power-grid sanity report.
source platform/Nangate45.pdn.tcl
pdngen -verbose
global_connect
report_design_area
