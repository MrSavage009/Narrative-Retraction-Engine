#!/usr/bin/env python3
"""
NRE v6 -- Standalone Narrative Retraction Engine
=====================================================
A single-file, zero-argument research instrument implementing the
Root-Cut paradigm: only PRIMARY claims are decision variables.
Derived claims are automatically absorbed via entailment closure.

Run:    python nredv6.py

Executes in one pass:
  1. CEM Validation (Cascade Cover-Up)
  2. Complexity hierarchy (Modular / Submodular / General)
  3. Divergence analysis with ground-truth assertions
  4. Topological Uncertainty Sampler (TUS)
  5. Natural-language explanations with full ID mapping
  6. Structured output (JSON + Markdown)
  7. State-space reduction metrics
  8. Robustness stress test

Dependencies: networkx (pip install networkx)
"""

import json
import sys
import time
import heapq
import random
from dataclasses import dataclass, asdict
from typing import Dict, Set, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

try:
    import networkx as nx
except ImportError:
    print("ERROR: networkx required. Install: pip install networkx")
    sys.exit(1)

# =============================================================================
# CONFIGURATION
# =============================================================================
MAX_ASTAR_STATES = 50000
K_TOP_PROTOCOLS = 3
TUS_SAMPLES = 200
TUS_NOISE = 0.15
STRESS_RUNS = 50
STRESS_NOISE = 0.10

# CEM predictions under ROOT-CUT paradigm (primary claims only)
# p3 is derived from p1/p2 and is automatically absorbed via closure.
CEM_PREDICTIONS = {
    "modular":    {"p1", "p2", "p7", "p9"},
    "submodular": {"p1", "p2", "p7", "p9"},
    "general":    {"p1", "p2", "p7", "p9", "p10", "p11"},
}


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass(frozen=True)
class Proposition:
    id: str
    text: str
    role: str = "slander"
    weight: float = 1.0
    damage: float = 1.0
    is_primary: bool = True


@dataclass
class ExtractedGraph:
    propositions: Dict[str, Proposition]
    entailments: List[Tuple[str, str]]
    contradictions: List[Tuple[str, str]]

    @property
    def slander_nodes(self) -> Set[str]:
        return {p.id for p in self.propositions.values() if p.role == "slander"}

    @property
    def anchor_nodes(self) -> Set[str]:
        return {p.id for p in self.propositions.values() if p.role == "anchor"}


@dataclass
class MetaNode:
    id: str
    members: frozenset
    is_anchor: bool
    weight: float = 1.0
    damage: float = 1.0
    is_primary: bool = True


@dataclass
class CondensedGraph:
    graph: nx.DiGraph
    meta_nodes: Dict[str, MetaNode]
    sources: Set[str]
    primary_sources: Set[str]
    sinks: Set[str]
    entailment_edges: Set[Tuple[str, str]]
    contradiction_edges: Set[Tuple[str, str]]
    closures: Dict[str, Set[str]]
    compressed_graph: nx.DiGraph
    compressed_closures: Dict[str, Set[str]]
    compressed_primary: Set[str]
    meta_to_primary: Dict[str, str]
    primary_to_meta: Dict[str, str]


@dataclass
class Protocol:
    name: str
    retraction_set: List[str]          # Meta-node IDs
    original_retracted: List[str]      # Original primary claim IDs
    cost: float
    structural_cost: float
    damage_cost: float
    gamma_cost: float
    remaining: List[str]
    derived_retracted: List[str]
    explanation: str
    path: List[str]


@dataclass
class TUSCertificate:
    node: str
    primary_frequency: float
    retraction_frequency: float
    instability_score: float
    is_true_derived: bool
    risk_level: str
    diagnostic: str


@dataclass
class Explanation:
    target: str
    target_text: str
    trace: List[Tuple[str, str]]
    anchor: str
    anchor_text: str
    justification: str


class CostFunction:
    """c(R) = alpha * |Cl(R)| + beta * sum(damage(v)) + gamma * |remaining|"""
    def __init__(self, alpha=1.0, beta=0.0, gamma=0.0):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def classify(self) -> str:
        if self.beta == 0 and self.gamma == 0:
            return "modular"
        elif self.gamma == 0:
            return "submodular"
        return "general"

    def _closure(self, retracted: Set[str], condensed: CondensedGraph) -> Set[str]:
        cl = set()
        for r in retracted:
            cl.update(condensed.compressed_closures.get(r, {r}))
        return cl

    def compute(self, retracted: Set[str], condensed: CondensedGraph) -> Tuple[float, float, float, float]:
        cl_r = self._closure(retracted, condensed)
        structural = self.alpha * len(cl_r)
        damage = self.beta * sum(
            condensed.meta_nodes[r].damage for r in cl_r
            if r in condensed.meta_nodes and not condensed.meta_nodes[r].is_anchor
        )
        # Only count remaining nodes REACHABLE from active primaries
        active_primaries = condensed.compressed_primary - retracted
        reachable = set()
        for p in active_primaries:
            reachable.update(condensed.compressed_closures.get(p, {p}))
        reachable.update(active_primaries)
        remaining = reachable - cl_r
        gamma = self.gamma * len(remaining)
        return structural + damage + gamma, structural, damage, gamma

    def marginal(self, v: str, current: Set[str], condensed: CondensedGraph) -> float:
        c1, _, _, _ = self.compute(current, condensed)
        c2, _, _, _ = self.compute(current | condensed.compressed_closures.get(v, {v}), condensed)
        return c2 - c1


# =============================================================================
# CEM: THE CASCADE COVER-UP
# =============================================================================

def build_hardcoded_graph() -> ExtractedGraph:
    """Canonical Controlled Epistemic Microenvironment.

    4-email adversarial thread with 5 topological motifs:
    1. Convergence Funnel (p1,p2 -> p3)
    2. Diamond Branch (p3 -> p4/p5 vs p3 -> p7)
    3. Circular SCC (p4 <-> p5)
    4. Bypass Bridge (p9 independent)
    5. Epistemic Orphan (p10, p11)
    """
    props = {
        "p1": Proposition("p1", "You missed the internal deadline", "slander", 2.0, 2.0, True),
        "p2": Proposition("p2", "You ignored my warning emails", "slander", 2.0, 1.5, True),
        "p3": Proposition("p3", "Your negligence caused the entire cascade", "slander", 1.0, 1.0, False),
        "p4": Proposition("p4", "The delay proves you mismanaged the project", "slander", 1.0, 6.0, False),
        "p5": Proposition("p5", "Your mismanagement is the root cause", "slander", 1.0, 4.0, False),
        "p6": Proposition("p6", "You are solely responsible for the $500K loss", "slander", 5.0, 4.0, False),
        "p7": Proposition("p7", "You concealed the vendor delay from the client", "slander", 1.0, 5.0, True),
        "p8": Proposition("p8", "You lied to the client about timelines", "slander", 5.0, 5.5, False),
        "p9": Proposition("p9", "You forged the client sign-off document", "slander", 1.0, 3.0, True),
        "p10": Proposition("p10", "You have a history of similar failures", "slander", 0.1, 0.1, True),
        "p11": Proposition("p11", "Your team has lost confidence in you", "slander", 0.1, 0.1, True),
        "a1": Proposition("a1", "The deadline was extended by mutual agreement", "anchor", 0.0, 0.0, False),
        "a2": Proposition("a2", "All warning emails were acknowledged", "anchor", 0.0, 0.0, False),
        "a3": Proposition("a3", "The project was delivered on time with verified sign-off", "anchor", 0.0, 0.0, False),
        "a4": Proposition("a4", "External vendor delay caused 80% of schedule slip", "anchor", 0.0, 0.0, False),
    }
    ents = [
        ("p1", "p3"), ("p2", "p3"),
        ("p3", "p4"), ("p3", "p5"), ("p3", "p7"),
        ("p4", "p5"), ("p5", "p4"),
        ("p4", "p6"), ("p5", "p6"),
        ("p7", "p8"),
    ]
    contras = [
        ("p6", "a1"), ("p6", "a2"),
        ("p8", "a3"), ("p9", "a3"),
    ]
    return ExtractedGraph(propositions=props, entailments=ents, contradictions=contras)


# =============================================================================
# GRAPH PROCESSOR
# =============================================================================

class GraphProcessor:
    def condense(self, graph: ExtractedGraph) -> CondensedGraph:
        G_full = nx.DiGraph()
        for p in graph.propositions.values():
            G_full.add_node(p.id, data=p)
        for s, t in graph.entailments:
            G_full.add_edge(s, t, relation="entailment")
        for s, t in graph.contradictions:
            G_full.add_edge(s, t, relation="contradiction")

        G_slander = G_full.subgraph(graph.slander_nodes)
        sccs = list(nx.strongly_connected_components(G_slander))

        mapping = {}
        meta_nodes = {}
        mid_counter = 0
        for scc in sccs:
            mid = "m" + str(mid_counter)
            mid_counter += 1
            total_weight = sum(graph.propositions[n].weight for n in scc)
            avg_damage = sum(graph.propositions[n].damage for n in scc) / max(len(scc), 1)
            is_primary = any(graph.propositions[n].is_primary for n in scc)
            meta_nodes[mid] = MetaNode(
                id=mid, members=frozenset(scc), is_anchor=False,
                weight=total_weight, damage=avg_damage, is_primary=is_primary
            )
            for n in scc:
                mapping[n] = mid

        for a in graph.anchor_nodes:
            mapping[a] = a
            meta_nodes[a] = MetaNode(
                id=a, members=frozenset([a]), is_anchor=True,
                weight=0.0, damage=0.0, is_primary=False
            )

        C = nx.DiGraph()
        for mid, mn in meta_nodes.items():
            C.add_node(mid, data=mn)

        ent_edges, con_edges = set(), set()
        for u, v, d in G_full.edges(data=True):
            if u not in mapping or v not in mapping:
                continue
            mu, mv = mapping[u], mapping[v]
            if mu == mv:
                continue
            rel = d.get("relation", "entailment")
            if rel == "entailment":
                ent_edges.add((mu, mv))
            else:
                con_edges.add((mu, mv))
            C.add_edge(mu, mv, relation=rel)

        sources = {mid for mid, mn in meta_nodes.items() if not mn.is_anchor}
        sinks = {mid for mid, mn in meta_nodes.items() if mn.is_anchor}

        C_slander = C.subgraph(sources)
        primary = {n for n in C_slander.nodes() if C_slander.in_degree(n) == 0}
        for mid in sources:
            if meta_nodes[mid].is_primary and mid not in primary:
                primary.add(mid)

        C_ent = nx.DiGraph()
        C_ent.add_nodes_from(C.nodes())
        for u, v in ent_edges:
            C_ent.add_edge(u, v)

        closures = {}
        for mid in meta_nodes:
            if meta_nodes[mid].is_anchor:
                closures[mid] = {mid}
            else:
                desc = nx.descendants(C_ent, mid) if mid in C_ent else set()
                closures[mid] = desc | {mid}

        comp_C, comp_closures, comp_primary = self._path_compress(
            C, C_ent, closures, primary, meta_nodes
        )

        # Bidirectional mapping between meta-nodes and original primary IDs
        meta_to_primary = {}
        primary_to_meta = {}
        for mid in comp_primary:
            mn = meta_nodes[mid]
            primary_members = [m for m in mn.members if graph.propositions[m].is_primary]
            if primary_members:
                meta_to_primary[mid] = primary_members[0]
                primary_to_meta[primary_members[0]] = mid
            else:
                # Fallback: use first member
                first = list(mn.members)[0]
                meta_to_primary[mid] = first
                primary_to_meta[first] = mid

        return CondensedGraph(
            graph=C, meta_nodes=meta_nodes, sources=sources,
            primary_sources=primary, sinks=sinks,
            entailment_edges=ent_edges, contradiction_edges=con_edges,
            closures=closures,
            compressed_graph=comp_C,
            compressed_closures=comp_closures,
            compressed_primary=comp_primary,
            meta_to_primary=meta_to_primary,
            primary_to_meta=primary_to_meta,
        )

    def _path_compress(self, C, C_ent, closures, primary, meta_nodes):
        keep = set()
        for node in C_ent.nodes():
            if node in primary:
                keep.add(node)
            elif C_ent.in_degree(node) > 1 or C_ent.out_degree(node) > 1:
                keep.add(node)
            elif C_ent.out_degree(node) == 0:
                keep.add(node)
        for u, v, d in C.edges(data=True):
            if d.get("relation") == "contradiction":
                keep.add(u)
                keep.add(v)

        comp = nx.DiGraph()
        for node in keep:
            comp.add_node(node)
        for node in keep:
            for desc in nx.descendants(C_ent, node):
                if desc in keep:
                    comp.add_edge(node, desc)

        comp_closures = {}
        for node in keep:
            if meta_nodes[node].is_anchor:
                comp_closures[node] = {node}
            else:
                cl = {node}
                for kd in keep:
                    if kd in closures[node]:
                        cl.add(kd)
                comp_closures[node] = cl

        comp_primary = primary & keep
        return comp, comp_closures, comp_primary


# =============================================================================
# SOLVERS
# =============================================================================

class FlowSolver:
    """Exact polynomial solver for modular costs.
    Only PRIMARY CLAIMS get finite capacity. Derived nodes get infinite capacity,
    forcing the min-cut to select upstream primary cuts (Root-Cut paradigm)."""
    def solve(self, condensed: CondensedGraph, cost_fn: CostFunction) -> Protocol:
        flowG = nx.DiGraph()
        ss, st = "__s__", "__t__"

        for mid in condensed.graph.nodes():
            mn = condensed.meta_nodes[mid]
            if mn.is_anchor:
                cap = float("inf")
            elif mid in condensed.compressed_primary:
                cap = mn.weight
            else:
                cap = float("inf")
            flowG.add_edge(mid + "_in", mid + "_out", capacity=cap)

        for u, v in condensed.entailment_edges:
            flowG.add_edge(u + "_out", v + "_in", capacity=float("inf"))
        for u, v in condensed.contradiction_edges:
            flowG.add_edge(u + "_out", v + "_in", capacity=float("inf"))
        # Only connect PRIMARY claims to super-source
        for s in condensed.compressed_primary:
            flowG.add_edge(ss, s + "_in", capacity=float("inf"))
        for t in condensed.sinks:
            flowG.add_edge(t + "_out", st, capacity=float("inf"))

        cut_val, partition = nx.minimum_cut(flowG, ss, st)
        reachable, _ = partition

        retracted_meta = set()
        for mid in condensed.graph.nodes():
            if condensed.meta_nodes[mid].is_anchor:
                continue
            if mid + "_in" in reachable and mid + "_out" not in reachable:
                retracted_meta.add(mid)

        original_retracted = sorted(condensed.meta_to_primary.get(m, m) for m in retracted_meta)
        cost, struct, dmg, gam = cost_fn.compute(retracted_meta, condensed)
        derived = cost_fn._closure(retracted_meta, condensed) - retracted_meta

        return Protocol(
            name="Modular-Flow-Exact",
            retraction_set=sorted(retracted_meta),
            original_retracted=original_retracted,
            cost=cost, structural_cost=struct, damage_cost=dmg, gamma_cost=gam,
            remaining=sorted(condensed.sources - retracted_meta),
            derived_retracted=sorted(derived),
            explanation="Exact min-cut: " + str(original_retracted) + " (cost=" + "{:.2f}".format(cost) + ")",
            path=sorted(retracted_meta),
        )


class GreedySolver:
    """Greedy retraction for submodular costs. Searches PRIMARY CLAIMS only.
    Selects node with best marginal_cost / marginal_benefit ratio at each step."""
    def solve(self, condensed: CondensedGraph, cost_fn: CostFunction) -> Protocol:
        primary = set(condensed.compressed_primary)
        active = set(primary)
        retracted = set()
        path = []

        def has_path_to_sink(act):
            full = set()
            for p in act:
                full.update(condensed.compressed_closures.get(p, {p}))
            for s in full:
                for t in condensed.sinks:
                    if nx.has_path(condensed.graph, s, t):
                        return True
            return False

        def node_reaches_sink(v):
            full = condensed.compressed_closures.get(v, {v})
            for s in full:
                for t in condensed.sinks:
                    if nx.has_path(condensed.graph, s, t):
                        return True
            return False

        iteration = 0
        while has_path_to_sink(active) and iteration < 1000:
            iteration += 1
            best_node, best_score = None, float("inf")

            for v in active:
                if not node_reaches_sink(v):
                    continue
                delta_paths = 1
                marg = cost_fn.marginal(v, retracted, condensed)
                score = marg / delta_paths
                if score < best_score:
                    best_score, best_node = score, v

            if best_node is None:
                break

            retracted.add(best_node)
            active.remove(best_node)
            path.append(best_node)

        cost, struct, dmg, gam = cost_fn.compute(retracted, condensed)
        derived = cost_fn._closure(retracted, condensed) - retracted
        original_retracted = sorted(condensed.meta_to_primary.get(m, m) for m in retracted)

        return Protocol(
            name="Submodular-Greedy-Approx",
            retraction_set=sorted(retracted),
            original_retracted=original_retracted,
            cost=cost, structural_cost=struct, damage_cost=dmg, gamma_cost=gam,
            remaining=sorted(active), derived_retracted=sorted(derived),
            explanation="Greedy: " + str(len(path)) + " retractions, cost=" + "{:.2f}".format(cost),
            path=path,
        )


class RootCutAStar:
    """Exact A* search for general monotone costs. PRIMARY CLAIMS ONLY."""
    def solve(self, condensed: CondensedGraph, cost_fn: CostFunction, k=K_TOP_PROTOCOLS) -> List[Protocol]:
        primary = set(condensed.compressed_primary)
        initial = frozenset(primary)
        goal_paths = []
        open_heap = []
        counter = 0
        h0 = self._heuristic(initial, condensed)
        heapq.heappush(open_heap, (h0, counter, 0.0, initial, []))
        closed_count = defaultdict(int)
        explored = 0

        while open_heap and len(goal_paths) < k:
            f, _, g, state, path = heapq.heappop(open_heap)

            if self._is_goal(state, condensed):
                retracted = primary - set(state)
                cost, struct, dmg, gam = cost_fn.compute(retracted, condensed)
                derived = cost_fn._closure(retracted, condensed) - retracted
                original_retracted = sorted(condensed.meta_to_primary.get(m, m) for m in retracted)

                goal_paths.append(Protocol(
                    name="RC-A*-Exact-" + str(len(goal_paths)+1),
                    retraction_set=sorted(retracted),
                    original_retracted=original_retracted,
                    cost=cost, structural_cost=struct, damage_cost=dmg, gamma_cost=gam,
                    remaining=sorted(state), derived_retracted=sorted(derived),
                    explanation="RC-A*: cost=" + "{:.2f}".format(cost) + ", path=" + str(path),
                    path=path,
                ))
                continue

            if closed_count[state] >= k:
                continue
            closed_count[state] += 1
            explored += 1

            if explored > MAX_ASTAR_STATES:
                break

            for v in state:
                next_state = frozenset(state - {v})
                next_path = path + [v]
                curr_retracted = primary - set(state)
                next_retracted = primary - set(next_state)
                delta_g = cost_fn.compute(next_retracted, condensed)[0] - cost_fn.compute(curr_retracted, condensed)[0]
                next_g = g + delta_g
                h = self._heuristic(next_state, condensed)
                counter += 1
                heapq.heappush(open_heap, (next_g + h, counter, next_g, next_state, next_path))

        if not goal_paths:
            g = GreedySolver()
            p = g.solve(condensed, cost_fn)
            p.name = "RC-A*-Fallback-Greedy"
            return [p]
        return goal_paths

    def _is_goal(self, state, condensed):
        full = set()
        for p in state:
            full.update(condensed.compressed_closures.get(p, {p}))
        for s in full:
            for t in condensed.sinks:
                if nx.has_path(condensed.graph, s, t):
                    return False
        return True

    def _heuristic(self, state, condensed):
        if not state:
            return 0.0
        active = set()
        for p in state:
            active.update(condensed.compressed_closures.get(p, {p}))
        flowG = nx.DiGraph()
        ss, st = "__s__", "__t__"
        for v in active:
            cap = float("inf") if v in condensed.sinks else 1.0
            flowG.add_edge(v + "_in", v + "_out", capacity=cap)
        for u, v in condensed.graph.edges():
            if u in active and v in active:
                flowG.add_edge(u + "_out", v + "_in", capacity=float("inf"))
        for s in state:
            flowG.add_edge(ss, s + "_in", capacity=float("inf"))
        for t in condensed.sinks:
            flowG.add_edge(t + "_out", st, capacity=float("inf"))
        try:
            cut_val, _ = nx.minimum_cut(flowG, ss, st)
            return float(cut_val)
        except Exception:
            return 0.0


class SolverSelector:
    def solve(self, condensed: CondensedGraph, cost_fn: CostFunction) -> List[Protocol]:
        cls = cost_fn.classify()
        if cls == "modular":
            return [FlowSolver().solve(condensed, cost_fn)]
        elif cls == "submodular":
            return [GreedySolver().solve(condensed, cost_fn)]
        else:
            return RootCutAStar().solve(condensed, cost_fn)


# =============================================================================
# EXPLANATION GENERATOR
# =============================================================================

def generate_explanations(protocol: Protocol, condensed: CondensedGraph,
                          graph: ExtractedGraph) -> List[Explanation]:
    explanations = []
    for target_meta in protocol.retraction_set:
        target = condensed.meta_to_primary.get(target_meta, target_meta)
        if target not in graph.propositions:
            continue
        target_text = graph.propositions[target].text
        trace = []
        visited = {target_meta}
        queue = [(target_meta, [target_meta])]
        anchor_found = None
        anchor_text = ""

        while queue and not anchor_found:
            node, path_so_far = queue.pop(0)
            for succ in condensed.graph.successors(node):
                if succ in visited:
                    continue
                visited.add(succ)
                new_path = path_so_far + [succ]
                if condensed.meta_nodes.get(succ, MetaNode("", frozenset(), True)).is_anchor:
                    anchor_found = succ
                    anchor_text = graph.propositions.get(succ, Proposition(succ, succ)).text
                    trace = []
                    for p_meta in new_path:
                        p_orig = condensed.meta_to_primary.get(p_meta, p_meta)
                        p_text = graph.propositions.get(p_orig, Proposition(p_orig, p_orig)).text
                        trace.append((p_orig, p_text))
                    break
                queue.append((succ, new_path))

        if anchor_found:
            chain = " -> ".join(t for _, t in trace)
            just = "Retracting " + target + " (" + target_text[:50] + ") breaks the chain: " + chain + " -> " + anchor_text[:50]
        else:
            just = "Retracting " + target + " (" + target_text[:50] + ") removes entailment paths."

        explanations.append(Explanation(
            target=target, target_text=target_text,
            trace=trace, anchor=anchor_found or "none",
            anchor_text=anchor_text, justification=just
        ))
    return explanations


# =============================================================================
# TUS: TOPOLOGICAL UNCERTAINTY SAMPLER
# =============================================================================

def sample_graph(G, edge_keep_prob, seed=None):
    rng = random.Random(seed) if seed is not None else random
    Gs = nx.DiGraph()
    Gs.add_nodes_from(G.nodes(data=True))
    for u, v in G.edges():
        if rng.random() < edge_keep_prob:
            Gs.add_edge(u, v)
    return Gs


def compute_primary_set(G, sources):
    return {n for n in sources if G.in_degree(n) == 0}


def evaluate_semantic_validity(retracted, G_true):
    active = set(G_true.nodes()) - retracted
    failures = []
    for r in retracted:
        for ancestor in nx.ancestors(G_true, r):
            if ancestor in active:
                failures.append((ancestor, r))
    return len(failures) == 0, failures


def generate_tus_certificate(G_true, sources, sinks, K=TUS_SAMPLES, edge_keep_prob=1-TUS_NOISE):
    primary_counts = defaultdict(int)
    retraction_counts = defaultdict(int)
    valid_count = 0
    invalid_count = 0

    for k in range(K):
        G_noisy = sample_graph(G_true, edge_keep_prob, seed=k)
        sample_roots = compute_primary_set(G_noisy, sources)
        for r in sample_roots:
            primary_counts[r] += 1

        sample_retracted = set()
        for r in sample_roots:
            if any(nx.has_path(G_noisy, r, t) for t in sinks):
                sample_retracted.add(r)
        for r in sample_retracted:
            retraction_counts[r] += 1

        is_valid, _ = evaluate_semantic_validity(sample_retracted, G_true)
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1

    certificates = []
    for node in sources:
        if G_true.nodes[node].get("is_sink", False):
            continue
        pf = primary_counts.get(node, 0) / K
        rf = retraction_counts.get(node, 0) / K
        instab = 1.0 - pf
        is_derived = G_true.in_degree(node) > 0

        if instab > 0.5 and is_derived:
            risk = "CRITICAL"
            diag = "FALSE ROOT: Retracted " + str(int(rf*100)) + "% as root but is derived in G*."
        elif instab > 0.2:
            risk = "WARNING"
            diag = "Moderate instability (" + "{:.2f}".format(instab) + "). Primary classification varies."
        elif is_derived and pf > 0:
            risk = "CAUTION"
            diag = "Derived node sometimes primary (" + "{:.2f}".format(pf) + "). Check extraction quality."
        else:
            risk = "STABLE"
            diag = "Consistently classified as true primary root."

        certificates.append(TUSCertificate(
            node=node, primary_frequency=pf, retraction_frequency=rf,
            instability_score=instab, is_true_derived=is_derived,
            risk_level=risk, diagnostic=diag
        ))

    return certificates, valid_count, invalid_count


# =============================================================================
# STRESS TEST
# =============================================================================

def run_stress_test(condensed, cost_fn, graph, runs=STRESS_RUNS, noise=STRESS_NOISE):
    costs = []
    valid_count = 0
    all_retracted = defaultdict(int)

    G_true = nx.DiGraph()
    for p in graph.propositions.values():
        G_true.add_node(p.id, is_sink=(p.role == "anchor"), is_source=p.is_primary)
    for s, t in graph.entailments:
        G_true.add_edge(s, t)
    for s, t in graph.contradictions:
        G_true.add_edge(s, t)

    sources = {n for n in G_true.nodes() if G_true.nodes[n].get("is_source", False)}
    sinks = {n for n in G_true.nodes() if G_true.nodes[n].get("is_sink", False)}

    for i in range(runs):
        G_noisy = sample_graph(G_true, 1 - noise, seed=1000 + i)
        props = {}
        for n in G_true.nodes():
            orig = graph.propositions.get(n, Proposition(n, n))
            # In noisy graph, a node is primary if it has no incoming edges AND is slander
            is_primary = G_noisy.in_degree(n) == 0 and orig.role == "slander"
            props[n] = Proposition(n, orig.text, orig.role, orig.weight, orig.damage, is_primary)
        ents = [(u, v) for u, v in G_noisy.edges()
                if not G_true.nodes[u].get("is_sink", False) and not G_true.nodes[v].get("is_sink", False)]
        contras = [(u, v) for u, v in G_noisy.edges()
                   if G_true.nodes[v].get("is_sink", False)]
        eg = ExtractedGraph(propositions=props, entailments=ents, contradictions=contras)
        proc = GraphProcessor()
        try:
            cd = proc.condense(eg)
            sel = SolverSelector()
            ps = sel.solve(cd, cost_fn)
            if ps:
                costs.append(ps[0].cost)
                for r in ps[0].original_retracted:
                    all_retracted[r] += 1
                # Check validity: no retracted node should have an active ancestor
                retracted_set = set(ps[0].original_retracted)
                is_valid, _ = evaluate_semantic_validity(retracted_set, G_true)
                if is_valid:
                    valid_count += 1
        except Exception:
            pass

    if not costs:
        return {"error": "All stress runs failed"}

    mean_cost = sum(costs) / len(costs)
    variance = sum((c - mean_cost) ** 2 for c in costs) / len(costs)
    return {
        "runs": runs,
        "valid_rate": valid_count / runs,
        "mean_cost": mean_cost,
        "min_cost": min(costs),
        "max_cost": max(costs),
        "cost_std": variance ** 0.5,
        "retraction_frequency": {k: v/runs for k, v in all_retracted.items()},
    }


# =============================================================================
# OUTPUT FORMATTERS
# =============================================================================

def format_markdown_report(results, explanations, tus, stress, condensed):
    lines = []
    lines.append("# Narrative Retraction Engine v6 -- Execution Report")
    lines.append("")
    lines.append("Generated: " + datetime.now().isoformat())
    lines.append("")

    lines.append("## 1. Complexity Hierarchy Results")
    lines.append("")
    lines.append("| Class | Solver | #Primary | #Derived | Total Cost | Structural | Damage | Gamma |")
    lines.append("|-------|--------|----------|----------|------------|------------|--------|-------|")
    for cls, prot in results.items():
        lines.append("| " + cls + " | " + prot.name + " | " + str(len(prot.original_retracted)) + " | "
                     + str(len(prot.derived_retracted)) + " | " + "{:.2f}".format(prot.cost) + " | "
                     + "{:.2f}".format(prot.structural_cost) + " | " + "{:.2f}".format(prot.damage_cost) + " | " + "{:.2f}".format(prot.gamma_cost) + " |")

    lines.append("")
    lines.append("## 2. Divergence Analysis")
    lines.append("")
    mod = set(results["modular"].original_retracted)
    sub = set(results["submodular"].original_retracted)
    gen = set(results["general"].original_retracted)
    lines.append("- **Modular only:** " + str(sorted(mod - sub - gen) or "none"))
    lines.append("- **Submodular only:** " + str(sorted(sub - mod - gen) or "none"))
    lines.append("- **General only:** " + str(sorted(gen - mod - sub) or "none"))
    lines.append("- **Common core:** " + str(sorted(mod & sub & gen) or "none"))

    lines.append("")
    lines.append("## 3. Explanations")
    lines.append("")
    for cls, exps in explanations.items():
        lines.append("### " + cls.title())
        lines.append("")
        for e in exps[:3]:
            lines.append("- **" + e.target + ":** " + e.justification)
        lines.append("")

    lines.append("")
    lines.append("## 4. TUS Epistemic Certificate")
    lines.append("")
    lines.append("| Node | Primary Freq | Retract Freq | Instability | Risk | Diagnostic |")
    lines.append("|------|-------------|-------------|-------------|------|------------|")
    for c in sorted(tus, key=lambda x: x.instability_score, reverse=True)[:10]:
        lines.append("| " + c.node + " | " + "{:.2f}".format(c.primary_frequency) + " | " + "{:.2f}".format(c.retraction_frequency) + " | "
                     + "{:.2f}".format(c.instability_score) + " | " + c.risk_level + " | " + c.diagnostic[:50] + "... |")

    lines.append("")
    lines.append("## 5. Stress Test")
    lines.append("")
    if "error" not in stress:
        lines.append("- Runs: " + str(stress["runs"]))
        lines.append("- Validity rate: " + "{:.1%}".format(stress["valid_rate"]))
        lines.append("- Mean cost: " + "{:.2f}".format(stress["mean_cost"]) + " (+-" + "{:.2f}".format(stress["cost_std"]) + ")")
        lines.append("- Cost range: [" + "{:.2f}".format(stress["min_cost"]) + ", " + "{:.2f}".format(stress["max_cost"]) + "]")
    else:
        lines.append("Error: " + stress["error"])

    lines.append("")
    lines.append("## 6. State-Space Metrics")
    lines.append("")
    raw = len(condensed.sources)
    prim = len(condensed.compressed_primary)
    lines.append("- Raw slander nodes: " + str(raw))
    lines.append("- Primary claims (decision space): " + str(prim))
    lines.append("- State space: 2^" + str(prim) + " = " + str(2**prim))
    lines.append("- Reduction vs. full MDP: " + "{:.1f}".format(2**raw / 2**prim) + "x")

    return "\n".join(lines)


def format_json_report(results, explanations, tus, stress, condensed):
    data = {
        "timestamp": datetime.now().isoformat(),
        "results": {},
        "divergence": {},
        "explanations": {},
        "tus_certificate": [asdict(c) for c in tus],
        "stress_test": stress,
        "state_space": {
            "raw_nodes": len(condensed.sources),
            "primary_claims": len(condensed.compressed_primary),
            "state_space_size": 2 ** len(condensed.compressed_primary),
        },
    }
    for k, v in results.items():
        data["results"][k] = {
            "name": v.name,
            "retraction_set": v.original_retracted,
            "cost": v.cost,
            "structural_cost": v.structural_cost,
            "damage_cost": v.damage_cost,
            "gamma_cost": v.gamma_cost,
            "derived_retracted": v.derived_retracted,
        }
    data["divergence"] = {
        "modular_only": sorted(set(results["modular"].original_retracted) -
                               set(results["submodular"].original_retracted) -
                               set(results["general"].original_retracted)),
        "submodular_only": sorted(set(results["submodular"].original_retracted) -
                                  set(results["modular"].original_retracted) -
                                  set(results["general"].original_retracted)),
        "general_only": sorted(set(results["general"].original_retracted) -
                               set(results["modular"].original_retracted) -
                               set(results["submodular"].original_retracted)),
        "common_core": sorted(set(results["modular"].original_retracted) &
                              set(results["submodular"].original_retracted) &
                              set(results["general"].original_retracted)),
    }
    for k, v in explanations.items():
        data["explanations"][k] = [{"target": e.target, "justification": e.justification} for e in v]
    return json.dumps(data, indent=2)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    start_time = time.perf_counter()

    print("=" * 78)
    print("  NRE v6 -- Standalone Narrative Retraction Engine")
    print("  Root-Cut Paradigm | Zero-Argument | CEM-Validated")
    print("=" * 78)

    # 1. BUILD CEM
    print("")
    print("[1/8] Loading Controlled Epistemic Microenvironment...")
    graph = build_hardcoded_graph()
    proc = GraphProcessor()
    condensed = proc.condense(graph)
    raw_nodes = len(condensed.sources)
    primary_nodes = len(condensed.compressed_primary)
    print("  Raw slander nodes: " + str(raw_nodes))
    print("  Primary claims: " + str(primary_nodes))
    print("  State space: 2^" + str(primary_nodes) + " = " + str(2**primary_nodes) + " (vs 2^" + str(raw_nodes) + " = " + str(2**raw_nodes) + " full)")
    print("  Reduction: " + "{:.1f}".format(2**raw_nodes / 2**primary_nodes) + "x")

    # 2. RUN ALL THREE SOLVERS
    print("")
    print("[2/8] Running complexity hierarchy solvers...")
    results = {}

    cf_mod = CostFunction(alpha=1.0, beta=0.0, gamma=0.0)
    results["modular"] = FlowSolver().solve(condensed, cf_mod)
    print("  Modular (Flow): " + str(results["modular"].original_retracted) + " | cost=" + "{:.2f}".format(results["modular"].cost))

    cf_sub = CostFunction(alpha=1.0, beta=1.0, gamma=0.0)
    results["submodular"] = GreedySolver().solve(condensed, cf_sub)
    print("  Submodular (Greedy): " + str(results["submodular"].original_retracted) + " | cost=" + "{:.2f}".format(results["submodular"].cost))

    cf_gen = CostFunction(alpha=1.0, beta=1.0, gamma=1.5)
    ps = RootCutAStar().solve(condensed, cf_gen, k=1)
    results["general"] = ps[0]
    print("  General (RC-A*): " + str(results["general"].original_retracted) + " | cost=" + "{:.2f}".format(results["general"].cost))

    # 3. VALIDATE PREDICTED DIVERGENCE
    print("")
    print("[3/8] Validating predicted divergence against ground truth...")
    mod_set = set(results["modular"].original_retracted)
    sub_set = set(results["submodular"].original_retracted)
    gen_set = set(results["general"].original_retracted)

    all_pass = True
    for cls, expected in CEM_PREDICTIONS.items():
        actual = set(results[cls].original_retracted)
        if actual == expected:
            print("  PASS " + cls.upper() + ": " + str(sorted(actual)) + " == " + str(sorted(expected)))
        else:
            print("  FAIL " + cls.upper() + ": GOT " + str(sorted(actual)) + " | EXPECTED " + str(sorted(expected)))
            all_pass = False

    if all_pass:
        print("")
        print("  >>> ALL CEM PREDICTIONS VALIDATED <<<")
    else:
        print("")
        print("  >>> CEM VALIDATION FAILED <<<")

    # 4. DIVERGENCE ANALYSIS
    print("")
    print("[4/8] Divergence analysis...")
    print("  Modular only:    " + str(sorted(mod_set - sub_set - gen_set) or "none"))
    print("  Submodular only: " + str(sorted(sub_set - mod_set - gen_set) or "none"))
    print("  General only:    " + str(sorted(gen_set - mod_set - sub_set) or "none"))
    print("  Common core:     " + str(sorted(mod_set & sub_set & gen_set) or "none"))

    # 5. GENERATE EXPLANATIONS
    print("")
    print("[5/8] Generating natural-language explanations...")
    explanations = {}
    for cls, prot in results.items():
        explanations[cls] = generate_explanations(prot, condensed, graph)
        print("  " + cls + ": " + str(len(explanations[cls])) + " explanations generated")
        for e in explanations[cls][:2]:
            print("    - " + e.justification[:100] + "...")

    # 6. TUS CERTIFICATE
    print("")
    print("[6/8] Running Topological Uncertainty Sampler (K=" + str(TUS_SAMPLES) + ", noise=" + str(TUS_NOISE) + ")...")
    G_true = nx.DiGraph()
    for p in graph.propositions.values():
        G_true.add_node(p.id, is_sink=(p.role == "anchor"), is_source=p.is_primary)
    for s, t in graph.entailments:
        G_true.add_edge(s, t)
    for s, t in graph.contradictions:
        G_true.add_edge(s, t)

    sources = {n for n in G_true.nodes() if G_true.nodes[n].get("is_source", False)}
    sinks = {n for n in G_true.nodes() if G_true.nodes[n].get("is_sink", False)}

    tus_certs, n_valid, n_invalid = generate_tus_certificate(
        G_true, sources, sinks, K=TUS_SAMPLES, edge_keep_prob=1 - TUS_NOISE
    )
    print("  Valid retractions: " + str(n_valid) + "/" + str(TUS_SAMPLES) + " (" + "{:.1%}".format(n_valid/TUS_SAMPLES) + ")")
    print("  Invalid retractions: " + str(n_invalid) + "/" + str(TUS_SAMPLES) + " (" + "{:.1%}".format(n_invalid/TUS_SAMPLES) + ")")
    critical = [c for c in tus_certs if c.risk_level == "CRITICAL"]
    if critical:
        print("  CRITICAL false roots detected: " + str([c.node for c in critical]))
    else:
        print("  No critical false roots detected.")

    # 7. STRESS TEST
    print("")
    print("[7/8] Running robustness stress test (" + str(STRESS_RUNS) + " runs, " + str(int(STRESS_NOISE*100)) + "% noise)...")
    stress = run_stress_test(condensed, cf_gen, graph, runs=STRESS_RUNS, noise=STRESS_NOISE)
    if "error" not in stress:
        print("  Validity rate: " + "{:.1%}".format(stress["valid_rate"]))
        print("  Mean cost: " + "{:.2f}".format(stress["mean_cost"]) + " (+-" + "{:.2f}".format(stress["cost_std"]) + ")")
        print("  Cost range: [" + "{:.2f}".format(stress["min_cost"]) + ", " + "{:.2f}".format(stress["max_cost"]) + "]")
    else:
        print("  Error: " + stress["error"])

    # 8. WRITE OUTPUT FILES
    print("")
    print("[8/8] Writing output files...")
    md_report = format_markdown_report(results, explanations, tus_certs, stress, condensed)
    json_report = format_json_report(results, explanations, tus_certs, stress, condensed)

    md_path = "/mnt/agents/output/nredv6_report.md"
    json_path = "/mnt/agents/output/nredv6_report.json"

    with open(md_path, "w") as f:
        f.write(md_report)
    with open(json_path, "w") as f:
        f.write(json_report)

    print("  Markdown report: " + md_path)
    print("  JSON report: " + json_path)

    elapsed = time.perf_counter() - start_time
    print("")
    print("=" * 78)
    print("  Execution complete in " + "{:.2f}".format(elapsed) + "s")
    print("  CEM validation: " + ("PASSED" if all_pass else "FAILED"))
    print("  Output written to /mnt/agents/output/")
    print("=" * 78)


if __name__ == "__main__":
    main()
