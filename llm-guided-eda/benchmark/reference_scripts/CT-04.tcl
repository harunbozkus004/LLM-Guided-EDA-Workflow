# Root clock buffer BUF_X8, all other clock-tree buffers BUF_X2.
# In this build -root_buf also becomes the master of every H-tree buffer, so
# the tree is built with BUF_X2 and the root buffer is upsized afterwards.
clock_tree_synthesis -root_buf BUF_X2 -buf_list BUF_X2

set block [ord::get_db_block]
set clk_net [[$block findBTerm clk] getNet]
set roots {}
foreach it [$clk_net getITerms] {
  if {[$it isInputSignal]} { lappend roots [[$it getInst] getName] }
}
foreach r $roots {
  replace_cell $r BUF_X8
}
puts "upsized root buffer(s): $roots"

detailed_placement
check_placement
