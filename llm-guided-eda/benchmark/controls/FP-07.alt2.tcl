# Alternative: configuration file, untrimmed build (keeps extra configured metal7 straps), explicit reconnect.
source platform/Nangate45.pdn.tcl
pdngen -skip_trim
global_connect
