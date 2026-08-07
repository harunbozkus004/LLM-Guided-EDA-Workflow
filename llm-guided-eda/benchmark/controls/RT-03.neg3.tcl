# Mistake: platform-default clock layers (metal6-metal10) instead of the requested metal4-metal6.
set_routing_layers -signal metal2-metal6 -clock metal6-metal10
global_route
