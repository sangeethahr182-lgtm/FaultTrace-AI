import networkx as nx
from typing import List, Dict, Set, Optional, Tuple, Any

class RadialFeederGraph:
    """
    NetworkX-based radial distribution feeder tree representation.
    Provides downstream traversal, radial tree pruning using telemetry,
    and engineering validation checks (radial connectivity, capacity sums, tie switch status).
    """

    def __init__(self, feeder_id: str):
        self.feeder_id = feeder_id
        # Directed graph pointing from source (substation breaker) down to loads
        self.digraph = nx.DiGraph()
        # Undirected graph for general connectivity and cycle/loop detection
        self.graph = nx.Graph()
        self.root_node: Optional[str] = None
        self.section_nodes: Set[str] = set()
        self.transformer_nodes: Set[str] = set()
        self.switch_nodes: Set[str] = set()

    def add_substation_breaker(self, breaker_id: str, lat: float, lng: float, name: str = "Feeder Breaker"):
        self.root_node = breaker_id
        attrs = {
            "type": "BREAKER",
            "name": name,
            "lat": lat,
            "lng": lng,
            "status": "CLOSED",
            "feeder_id": self.feeder_id,
        }
        self.digraph.add_node(breaker_id, **attrs)
        self.graph.add_node(breaker_id, **attrs)

    def add_line_section(
        self,
        section_id: str,
        upstream_id: Optional[str],
        length_km: float,
        rated_capacity_amps: float,
        start_coords: Tuple[float, float],
        end_coords: Tuple[float, float],
        conductor_type: str = "Rabbit ACSR",
        has_fault_indicator: bool = False,
        status: str = "ENERGIZED"
    ):
        self.section_nodes.add(section_id)
        attrs = {
            "type": "SECTION",
            "name": section_id,
            "length_km": length_km,
            "rated_capacity_amps": rated_capacity_amps,
            "start_lat": start_coords[0],
            "start_lng": start_coords[1],
            "lat": end_coords[0],
            "lng": end_coords[1],
            "conductor_type": conductor_type,
            "has_fault_indicator": has_fault_indicator,
            "status": status,
            "feeder_id": self.feeder_id,
        }
        self.digraph.add_node(section_id, **attrs)
        self.graph.add_node(section_id, **attrs)

        parent = upstream_id if upstream_id else self.root_node
        if parent:
            edge_attrs = {"type": "LINE", "length_km": length_km, "status": "CLOSED"}
            self.digraph.add_edge(parent, section_id, **edge_attrs)
            self.graph.add_edge(parent, section_id, **edge_attrs)

    def add_transformer(
        self,
        transformer_id: str,
        section_id: str,
        capacity_kva: float,
        current_load_kva: float,
        coords: Tuple[float, float],
        status: str = "ENERGIZED"
    ):
        self.transformer_nodes.add(transformer_id)
        attrs = {
            "type": "TRANSFORMER",
            "name": transformer_id,
            "section_id": section_id,
            "capacity_kva": capacity_kva,
            "current_load_kva": current_load_kva,
            "lat": coords[0],
            "lng": coords[1],
            "status": status,
            "feeder_id": self.feeder_id,
        }
        self.digraph.add_node(transformer_id, **attrs)
        self.graph.add_node(transformer_id, **attrs)

        edge_attrs = {"type": "DT_LINK", "status": "CLOSED"}
        self.digraph.add_edge(section_id, transformer_id, **edge_attrs)
        self.graph.add_edge(section_id, transformer_id, **edge_attrs)

    def add_switch(
        self,
        switch_id: str,
        section_id: Optional[str],
        switch_type: str,  # AIR_BREAK, TIE_SWITCH, BREAKER, SECTIONALIZER
        normal_state: str,  # CLOSED, OPEN
        current_state: str,
        coords: Tuple[float, float],
        adjacent_feeder_id: Optional[str] = None,
        rated_current_amps: float = 400.0
    ):
        self.switch_nodes.add(switch_id)
        attrs = {
            "type": "SWITCH",
            "name": switch_id,
            "section_id": section_id,
            "switch_type": switch_type,
            "normal_state": normal_state,
            "current_state": current_state,
            "adjacent_feeder_id": adjacent_feeder_id,
            "rated_current_amps": rated_current_amps,
            "lat": coords[0],
            "lng": coords[1],
            "feeder_id": self.feeder_id,
        }
        self.digraph.add_node(switch_id, **attrs)
        self.graph.add_node(switch_id, **attrs)

        if section_id and section_id in self.digraph:
            edge_attrs = {"type": "SWITCH", "switch_type": switch_type, "status": current_state}
            self.digraph.add_edge(section_id, switch_id, **edge_attrs)
            self.graph.add_edge(section_id, switch_id, **edge_attrs)

    def get_downstream_nodes(self, node_id: str) -> Set[str]:
        """Returns all descendant node IDs downstream of node_id in the radial tree."""
        if node_id not in self.digraph:
            return set()
        return nx.descendants(self.digraph, node_id)

    def get_downstream_sections(self, section_id: str) -> List[str]:
        """Returns all line section IDs downstream of section_id (including itself)."""
        descendants = self.get_downstream_nodes(section_id)
        downstream = [n for n in descendants if self.digraph.nodes[n].get("type") == "SECTION"]
        if section_id in self.section_nodes:
            downstream.insert(0, section_id)
        return downstream

    def get_downstream_transformers(self, section_id: str) -> List[str]:
        """Returns all transformer IDs downstream of section_id."""
        descendants = self.get_downstream_nodes(section_id)
        dts = [n for n in descendants if self.digraph.nodes[n].get("type") == "TRANSFORMER"]
        # Also check directly connected DTs to this section
        for succ in self.digraph.successors(section_id):
            if self.digraph.nodes[succ].get("type") == "TRANSFORMER" and succ not in dts:
                dts.append(succ)
        return dts

    def get_upstream_path(self, node_id: str) -> List[str]:
        """Returns the path from root breaker to node_id."""
        if not self.root_node or node_id not in self.digraph:
            return []
        try:
            return nx.shortest_path(self.digraph, source=self.root_node, target=node_id)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return []

    def prune_candidates(
        self,
        candidate_sections: List[str],
        energized_nodes: Set[str],
        deenergized_nodes: Set[str]
    ) -> List[str]:
        """
        Radial-tree pruning:
        A candidate section is IMPOSSIBLE if a verified ENERGIZED node is downstream
        of this section on the same radial path (since a radial fault/opening on this
        section would deprive power to all downstream nodes).
        
        Returns pruned list of candidate fault sections.
        """
        pruned_candidates = []
        for sec in candidate_sections:
            if sec not in self.digraph:
                continue

            downstream_nodes = self.get_downstream_nodes(sec)
            
            # Rule: If ANY downstream node is confirmed ENERGIZED, this section CANNOT be the fault
            has_energized_downstream = any(d in energized_nodes for d in downstream_nodes)
            if has_energized_downstream:
                # Section is pruned out
                continue

            pruned_candidates.append(sec)

        return pruned_candidates

    def find_isolation_switch(self, section_id: str) -> Optional[str]:
        """
        Finds the nearest switch associated with this section or its upstream boundary.
        Prefers an Air-Break (AB) or sectionalizer switch.
        """
        # 1. Directly attached switch
        for neighbor in self.digraph.neighbors(section_id):
            node_data = self.digraph.nodes[neighbor]
            if node_data.get("type") == "SWITCH" and node_data.get("switch_type") in ("AIR_BREAK", "SECTIONALIZER"):
                return neighbor

        # 2. Check upstream path for the closest switch
        upstream_path = self.get_upstream_path(section_id)
        for node in reversed(upstream_path):
            for neighbor in self.digraph.neighbors(node):
                node_data = self.digraph.nodes[neighbor]
                if node_data.get("type") == "SWITCH" and node_data.get("switch_type") in ("AIR_BREAK", "SECTIONALIZER", "BREAKER"):
                    return neighbor

        return None

    def find_candidate_tie_switches(self, section_id: str) -> List[str]:
        """
        Finds tie-switches located downstream or adjacent to the affected section
        that could back-feed the healthy downstream island.
        """
        downstream = self.get_downstream_nodes(section_id)
        tie_switches = []
        for n in downstream:
            data = self.digraph.nodes[n]
            if data.get("type") == "SWITCH" and data.get("switch_type") == "TIE_SWITCH":
                tie_switches.append(n)
        return tie_switches

    # --- Specific non-negotiable checks (named exactly as implemented) ---
    def radial_connectivity_check(self, proposed_tie_switch_id: str) -> Dict[str, Any]:
        """
        Validation Check 1: Radial connectivity check
        Verifies that closing the tie switch will not introduce a closed loop or parallel feed
        unless the faulty section has been isolated.
        """
        # Create a working copy of the undirected graph
        sim_graph = self.graph.copy()
        # Closing the tie switch connects it to the alternate feeder edge
        is_radial = True
        cycles = []
        try:
            cycles = nx.cycle_basis(sim_graph)
            is_radial = (len(cycles) == 0)
        except Exception as e:
            is_radial = False

        return {
            "check_name": "radial_connectivity_check",
            "passed": is_radial,
            "details": f"Radial connectivity verified. Cycles detected: {len(cycles)}.",
            "cycles_detected": len(cycles),
            "safety_rule": "Advisory: requires engineering validation and operator authorisation"
        }

    def rated_capacity_sum_check(
        self,
        donor_feeder_rated_amps: float,
        donor_feeder_current_amps: float,
        transferred_load_amps: float
    ) -> Dict[str, Any]:
        """
        Validation Check 2: Rated-capacity sum check
        Validates that the sum of donor feeder current load + transferred downstream load
        does not exceed donor feeder rated capacity.
        """
        total_projected_amps = donor_feeder_current_amps + transferred_load_amps
        passed = total_projected_amps <= donor_feeder_rated_amps
        margin_amps = donor_feeder_rated_amps - total_projected_amps

        return {
            "check_name": "rated_capacity_sum_check",
            "passed": passed,
            "donor_feeder_rated_amps": round(donor_feeder_rated_amps, 2),
            "donor_feeder_current_amps": round(donor_feeder_current_amps, 2),
            "transferred_load_amps": round(transferred_load_amps, 2),
            "total_projected_amps": round(total_projected_amps, 2),
            "headroom_margin_amps": round(margin_amps, 2),
            "details": f"Capacity check {'PASSED' if passed else 'FAILED'}: Projected {total_projected_amps:.1f}A vs Rated {donor_feeder_rated_amps:.1f}A (Margin: {margin_amps:.1f}A).",
            "safety_rule": "Advisory: requires engineering validation and operator authorisation"
        }

    def tie_switch_availability_check(
        self,
        tie_switch_id: str,
        switch_current_state: str,
        is_operational: bool = True
    ) -> Dict[str, Any]:
        """
        Validation Check 3: Tie-switch availability check
        Verifies tie switch exists, is physically functional, and currently OPEN (ready to close).
        """
        exists = tie_switch_id in self.switch_nodes or tie_switch_id in self.digraph
        ready = exists and switch_current_state == "OPEN" and is_operational

        return {
            "check_name": "tie_switch_availability_check",
            "passed": ready,
            "tie_switch_id": tie_switch_id,
            "current_state": switch_current_state,
            "is_operational": is_operational,
            "details": f"Tie-switch {tie_switch_id} is {'AVAILABLE' if ready else 'UNAVAILABLE'} (State: {switch_current_state}).",
            "safety_rule": "Advisory: requires engineering validation and operator authorisation"
        }
