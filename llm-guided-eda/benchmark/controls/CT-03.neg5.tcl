# Modifies the design: upsizes the clock root buffer before reporting the skew.
replace_cell clkbuf_0_clk BUF_X8
estimate_parasitics -placement
report_clock_skew -setup -digits 4 > outputs/ct03_clock_skew.rpt
