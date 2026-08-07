# Alternative: explicit list of filler masters, followed by a legality check.
filler_placement -prefix FILL_ {FILLCELL_X32 FILLCELL_X16 FILLCELL_X8 FILLCELL_X4 FILLCELL_X2 FILLCELL_X1}
check_placement -verbose
