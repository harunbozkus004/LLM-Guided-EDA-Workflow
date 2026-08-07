# Wrong: the platform grid plus an extra, unconfigured set of metal4 straps.
source platform/Nangate45.pdn.tcl
add_pdn_stripe -grid grid -layer metal4 -width 0.48 -pitch 56.0 -offset 16
pdngen
