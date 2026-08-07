# Buffer list contains BUF_X4 but starts with BUF_X2: the first cell becomes
# the root buffer and, in this build, the master of every tree buffer.
clock_tree_synthesis -buf_list {BUF_X2 BUF_X4}
