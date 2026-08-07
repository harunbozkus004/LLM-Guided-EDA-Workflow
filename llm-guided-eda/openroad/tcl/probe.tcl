# Design-state probe (harness-owned; never shown to or editable by the agent).
#
# Runs after the agent script in the same OpenROAD session and writes
# probe.json describing the *actual* state of the design database. The probe
# is read-only: it never modifies the design. Validators and the agent's own
# state manager rely on this ground truth rather than on what the LLM claims.

namespace eval ::__probe {
  proc jstr {s} {
    set s [string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t] $s]
    regsub -all {[\x00-\x1f]} $s {} s
    return "\"$s\""
  }
  proc jnum {x} {
    if {[string is double -strict $x] && ![string match -nocase {*inf*} $x]
        && ![string match -nocase {*nan*} $x] && abs($x) < 1e30} {
      return $x
    }
    return null
  }
  proc jbool {b} { return [expr {$b ? "true" : "false"}] }
  proc jobj {pairs} {
    set parts {}
    foreach {k v} $pairs { lappend parts "[jstr $k]: $v" }
    return "\{[join $parts {, }]\}"
  }
  proc jlist {items} { return "\[[join $items {, }]\]" }
  proc jcounts {arr_name} {
    upvar 1 $arr_name a
    set pairs {}
    foreach k [lsort [array names a]] { lappend pairs $k $a($k) }
    return [jobj $pairs]
  }
  proc um {v dbu} { return [expr {double($v) / $dbu}] }
  proc rect {r dbu} {
    return [jlist [list [um [$r xMin] $dbu] [um [$r yMin] $dbu] [um [$r xMax] $dbu] [um [$r yMax] $dbu]]]
  }

  proc collect {} {
    set P {}
    lappend P script_status [jstr $::harness_script_status]
    set db [ord::get_db]
    set chip [$db getChip]
    if {$chip == "NULL"} {
      lappend P design_loaded false
      return [jobj $P]
    }
    set block [$chip getBlock]
    set dbu [$block getDefUnits]
    lappend P design_loaded true top [jstr [$block getName]] dbu $dbu

    # ---- floorplan geometry
    set die [$block getDieArea]
    set die_w [expr {[$die xMax] - [$die xMin]}]
    set die_h [expr {[$die yMax] - [$die yMin]}]
    set core_ok 0
    if {![catch {set core [$block getCoreArea]}] && [$core xMax] > [$core xMin]} { set core_ok 1 }
    lappend P die [expr {$die_w > 0 ? [rect $die $dbu] : "null"}]
    lappend P die_area_um2 [expr {double($die_w) * $die_h / $dbu / $dbu}]
    if {$core_ok} {
      set core_area [expr {double([$core xMax] - [$core xMin]) * ([$core yMax] - [$core yMin]) / $dbu / $dbu}]
      lappend P core [rect $core $dbu] core_area_um2 $core_area
    } else {
      set core_area 0.0
      lappend P core null core_area_um2 0.0
    }
    set rows [$block getRows]
    set site_name ""; set row_h 0
    if {[llength $rows]} {
      set site [[lindex $rows 0] getSite]
      set site_name [$site getName]; set row_h [um [$site getHeight] $dbu]
    }
    lappend P row_count [llength $rows] site [jstr $site_name] row_height_um $row_h
    set tg_layers {}
    foreach tg [$block getTrackGrids] { lappend tg_layers [jstr [[$tg getTechLayer] getName]] }
    lappend P track_grid_layers [jlist $tg_layers]

    # ---- instances
    array set by_status {}; array set by_type {}; array set by_master {}
    set n_inst 0; set n_filler 0; set n_tap 0; set n_seq 0; set n_buf 0; set n_inv 0
    set n_clkbuf_name 0; set n_logic_placed 0; set n_logic 0; set n_outside_core 0
    set logic_area 0.0; set phys_area 0.0; set pos {}
    foreach inst [$block getInsts] {
      incr n_inst
      set m [$inst getMaster]
      set mname [$m getName]; set mtype [$m getType]; set st [$inst getPlacementStatus]
      incr by_status($st) 0; incr by_status($st)
      incr by_type($mtype) 0; incr by_type($mtype)
      set area [expr {double([$m getWidth]) * [$m getHeight] / $dbu / $dbu}]
      if {[$m isFiller]} { incr n_filler; set phys_area [expr {$phys_area + $area}]; continue }
      incr by_master($mname) 0; incr by_master($mname)
      if {$mtype == "CORE_WELLTAP" || [string match TAPCELL* $mname]} {
        incr n_tap; set phys_area [expr {$phys_area + $area}]; continue
      }
      incr n_logic
      set logic_area [expr {$logic_area + $area}]
      if {[$m isSequential]} { incr n_seq }
      if {[string match BUF_* $mname] || [string match CLKBUF_* $mname]} { incr n_buf }
      if {[string match INV_* $mname]} { incr n_inv }
      if {[string match clkbuf* [$inst getName]]} { incr n_clkbuf_name }
      if {$st in {PLACED FIRM LOCKED COVER}} {
        incr n_logic_placed
        set bb [$inst getBBox]
        lappend pos "[jstr [$inst getName]]: [jlist [list [um [$bb xMin] $dbu] [um [$bb yMin] $dbu] [jstr [$inst getOrient]]]]"
        if {$core_ok && ([$bb xMin] < [$core xMin] || [$bb yMin] < [$core yMin]
                          || [$bb xMax] > [$core xMax] || [$bb yMax] > [$core yMax])} {
          incr n_outside_core
        }
      }
    }
    lappend P inst_count $n_inst logic_inst_count $n_logic filler_count $n_filler tapcell_count $n_tap
    lappend P sequential_count $n_seq buffer_count $n_buf inverter_count $n_inv clkbuf_named_count $n_clkbuf_name
    lappend P logic_placed_count $n_logic_placed logic_outside_core_count $n_outside_core
    lappend P logic_area_um2 $logic_area physical_only_area_um2 $phys_area
    lappend P utilization [expr {$core_area > 0 ? $logic_area / $core_area : "null"}]
    lappend P utilization_with_taps [expr {$core_area > 0 ? ($logic_area + [::__probe::tap_area $block $dbu]) / $core_area : "null"}]
    lappend P status_counts [jcounts by_status] type_counts [jcounts by_type] master_counts [jcounts by_master]
    lappend P positions "\{[join $pos {, }]\}"

    set legal null
    if {$n_logic > 0 && $n_logic_placed == $n_logic} {
      set legal [expr {[catch {check_placement}] ? "false" : "true"}]
    }
    lappend P placement_legal $legal

    # ---- IO pins
    set n_bt 0; set n_bt_placed 0; set pins {}
    foreach bt [$block getBTerms] {
      incr n_bt
      set placed 0; set layer ""; set cx null; set cy null
      foreach bp [$bt getBPins] {
        if {[$bp getPlacementStatus] in {PLACED FIRM LOCKED COVER}} { set placed 1 }
        set boxes [$bp getBoxes]
        if {[llength $boxes]} {
          set bx [lindex $boxes 0]
          set layer [[$bx getTechLayer] getName]
          set cx [um [expr {([$bx xMin] + [$bx xMax]) / 2}] $dbu]
          set cy [um [expr {([$bx yMin] + [$bx yMax]) / 2}] $dbu]
        }
      }
      if {$placed} { incr n_bt_placed }
      lappend pins "[jstr [$bt getName]]: [jobj [list placed [jbool $placed] layer [jstr $layer] x $cx y $cy io [jstr [$bt getIoType]] sig [jstr [$bt getSigType]]]]"
    }
    lappend P io_pin_count $n_bt io_pins_placed $n_bt_placed io_pins "\{[join $pins {, }]\}"

    # ---- nets, power grid, routing
    set n_net 0; set n_sig 0; set n_routable 0; set n_wired 0; set n_guided 0; set wl 0
    set special {}
    foreach net [$block getNets] {
      incr n_net
      if {[$net isSpecial]} {
        lappend special "[jstr [$net getName]]: [llength [$net getSWires]]"
        continue
      }
      if {[$net getSigType] in {POWER GROUND}} { continue }
      incr n_sig
      if {[$net getITermCount] + [$net getBTermCount] < 2} { continue }
      incr n_routable
      set w [$net getWire]
      if {$w != "NULL"} {
        incr n_wired
        if {![catch {$w getLength} len]} { set wl [expr {$wl + $len}] }
      }
      if {![catch {llength [$net getGuides]} ng] && $ng > 0} { incr n_guided }
    }
    lappend P net_count $n_net signal_net_count $n_sig routable_net_count $n_routable
    lappend P routed_net_count $n_wired guided_net_count $n_guided
    lappend P detailed_wirelength_um [um $wl $dbu]
    lappend P special_net_swires "\{[join $special {, }]\}"
    lappend P have_global_routes [expr {[catch {grt::have_routes} hr] ? "null" : [jbool $hr]}]
    lappend P drv_count [expr {[catch {detailed_route_num_drvs} drv] ? "null" : $drv}]

    # ---- clock network (register clock pins via STA)
    set clocks {}
    if {![catch {all_clocks} clks]} {
      foreach c $clks { lappend clocks [jstr [get_name $c]] }
    }
    lappend P clocks [jlist $clocks]
    array set ck_nets {}; array set ck_drivers {}
    set n_ck_pins 0
    if {![catch {all_registers -clock_pins} ckpins]} {
      foreach pin $ckpins {
        incr n_ck_pins
        set nets [get_nets -quiet -of_objects $pin]
        if {[llength $nets] == 0} { continue }
        set nname [get_full_name [lindex $nets 0]]
        set ck_nets($nname) 1
      }
      foreach nname [array names ck_nets] {
        set drv "PORT"
        foreach dp [get_pins -quiet -of_objects [get_nets $nname] -filter "direction==output"] {
          set cell [get_cells -of_objects $dp]
          set drv [get_property $cell ref_name]
        }
        incr ck_drivers($drv) 0; incr ck_drivers($drv)
      }
    }
    lappend P register_clock_pin_count $n_ck_pins clock_sink_net_count [array size ck_nets]
    lappend P clock_sink_net_drivers [jcounts ck_drivers]

    # ---- timing summary (depends on whatever parasitics the session holds)
    if {[llength $clocks]} {
      foreach {key cmd} {wns_setup {sta::worst_slack -max} tns_setup {sta::total_negative_slack -max}
                         wns_hold {sta::worst_slack -min} tns_hold {sta::total_negative_slack -min}} {
        if {[catch {set v [eval $cmd]}]} { set v null }
        lappend P $key [jnum $v]
      }
    }
    return [jobj $P]
  }

  proc tap_area {block dbu} {
    set a 0.0
    foreach inst [$block getInsts] {
      set m [$inst getMaster]
      if {[$m getType] == "CORE_WELLTAP" || [string match TAPCELL* [$m getName]]} {
        set a [expr {$a + double([$m getWidth]) * [$m getHeight] / $dbu / $dbu}]
      }
    }
    return $a
  }
}

if {[catch {set ::__probe_json [::__probe::collect]} ::__probe_err]} {
  puts "HARNESS_PROBE_ERROR: $::__probe_err"
  set ::__probe_json "\{\"probe_error\": [::__probe::jstr $::__probe_err]\}"
}
set ::__probe_fh [open probe.json w]
puts $::__probe_fh $::__probe_json
close $::__probe_fh
