import pytest
from app.graph.engine import RadialFeederGraph

@pytest.fixture
def sample_feeder_graph():
    g = RadialFeederGraph(feeder_id="F4")
    g.add_substation_breaker("CB-F4", 13.0358, 77.5970)
    
    # Trunk: S1 -> S2 -> S5
    g.add_line_section("F4-S1", None, 0.4, 400.0, (13.0358, 77.5970), (13.038, 77.598))
    g.add_line_section("F4-S2", "F4-S1", 0.5, 400.0, (13.038, 77.598), (13.040, 77.600))
    g.add_line_section("F4-S5", "F4-S2", 0.6, 400.0, (13.040, 77.600), (13.045, 77.602))
    
    # Branch A: S5 -> S6 -> S10
    g.add_line_section("F4-S6", "F4-S5", 0.5, 400.0, (13.045, 77.602), (13.048, 77.601))
    g.add_line_section("F4-S10", "F4-S6", 0.5, 400.0, (13.048, 77.601), (13.050, 77.598))
    
    # Branch B: S5 -> S14 -> S16
    g.add_line_section("F4-S14", "F4-S5", 0.7, 400.0, (13.045, 77.602), (13.052, 77.610))
    g.add_line_section("F4-S16", "F4-S14", 0.6, 400.0, (13.052, 77.610), (13.057, 77.613))

    # Add Transformers
    g.add_transformer("DT-08", "F4-S10", 500.0, 240.0, (13.050, 77.598), status="ENERGIZED")
    g.add_transformer("DT-14", "F4-S14", 315.0, 130.0, (13.052, 77.610), status="DE_ENERGIZED")
    g.add_transformer("DT-16", "F4-S16", 250.0, 95.0, (13.057, 77.613), status="DE_ENERGIZED")

    # Add Switches
    g.add_switch("AB-14", "F4-S14", "AIR_BREAK", "CLOSED", "CLOSED", (13.052, 77.610))
    g.add_switch("TS-08", "F4-S16", "TIE_SWITCH", "OPEN", "OPEN", (13.057, 77.613), adjacent_feeder_id="F3")

    return g


def test_downstream_traversal(sample_feeder_graph):
    # Downstream sections of S5 should include S6, S10, S14, S16 and S5
    downstream_s5 = sample_feeder_graph.get_downstream_sections("F4-S5")
    assert "F4-S5" in downstream_s5
    assert "F4-S6" in downstream_s5
    assert "F4-S10" in downstream_s5
    assert "F4-S14" in downstream_s5
    assert "F4-S16" in downstream_s5
    assert "F4-S1" not in downstream_s5

    # Downstream transformers of S14
    downstream_dts_s14 = sample_feeder_graph.get_downstream_transformers("F4-S14")
    assert "DT-14" in downstream_dts_s14
    assert "DT-16" in downstream_dts_s14
    assert "DT-08" not in downstream_dts_s14


def test_radial_tree_pruning(sample_feeder_graph):
    """
    Test non-negotiable rule:
    If a downstream node is verified ENERGIZED, the candidate section upstream of it
    is IMPOSSIBLE and must be pruned out.
    """
    all_candidates = ["F4-S1", "F4-S5", "F4-S6", "F4-S10", "F4-S14", "F4-S16"]
    
    # DT-08 is verified ENERGIZED; DT-14 and DT-16 are DE_ENERGIZED
    energized_nodes = {"DT-08"}
    deenergized_nodes = {"DT-14", "DT-16"}

    pruned = sample_feeder_graph.prune_candidates(all_candidates, energized_nodes, deenergized_nodes)

    # Since DT-08 (on branch A) is energized:
    # - F4-S6 and F4-S10 CANNOT be the fault (they are upstream of DT-08).
    # - F4-S1 and F4-S5 are also upstream of DT-08, so power reached DT-08, pruning them!
    # Therefore, only the isolated branch B (F4-S14, F4-S16) survives pruning!
    assert "F4-S10" not in pruned
    assert "F4-S6" not in pruned
    assert "F4-S14" in pruned
    assert "F4-S16" in pruned


def test_isolation_and_tie_switch_search(sample_feeder_graph):
    iso_sw = sample_feeder_graph.find_isolation_switch("F4-S14")
    assert iso_sw == "AB-14"

    tie_sw = sample_feeder_graph.find_candidate_tie_switches("F4-S14")
    assert "TS-08" in tie_sw


def test_engineering_validation_checks(sample_feeder_graph):
    # Check 1: Radial connectivity check
    rad_res = sample_feeder_graph.radial_connectivity_check("TS-08")
    assert rad_res["check_name"] == "radial_connectivity_check"
    assert rad_res["passed"] is True
    assert "Advisory" in rad_res["safety_rule"]

    # Check 2: Rated-capacity sum check (Passing case: 160A load + 30A transfer <= 400A rated)
    cap_pass = sample_feeder_graph.rated_capacity_sum_check(
        donor_feeder_rated_amps=400.0,
        donor_feeder_current_amps=160.0,
        transferred_load_amps=30.0
    )
    assert cap_pass["check_name"] == "rated_capacity_sum_check"
    assert cap_pass["passed"] is True
    assert cap_pass["headroom_margin_amps"] == 210.0

    # Check 2: Rated-capacity sum check (Failing case: 380A load + 50A transfer > 400A rated)
    cap_fail = sample_feeder_graph.rated_capacity_sum_check(
        donor_feeder_rated_amps=400.0,
        donor_feeder_current_amps=380.0,
        transferred_load_amps=50.0
    )
    assert cap_fail["passed"] is False
    assert cap_fail["headroom_margin_amps"] < 0

    # Check 3: Tie-switch availability check
    tie_pass = sample_feeder_graph.tie_switch_availability_check("TS-08", switch_current_state="OPEN")
    assert tie_pass["passed"] is True

    tie_fail = sample_feeder_graph.tie_switch_availability_check("TS-08", switch_current_state="CLOSED")
    assert tie_fail["passed"] is False
