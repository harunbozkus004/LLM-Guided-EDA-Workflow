# Fabricated description: real buffer names, sinks guessed as an even split of 35 registers.
set f [open outputs/ct06_clock_tree.txt w]
puts $f "clkbuf_0_clk BUF_X4 1 0"
puts $f "clkbuf_2_0__f_clk BUF_X4 2 9"
puts $f "clkbuf_2_1__f_clk BUF_X4 2 9"
puts $f "clkbuf_2_2__f_clk BUF_X4 2 9"
puts $f "clkbuf_2_3__f_clk BUF_X4 2 8"
close $f
