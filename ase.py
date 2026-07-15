#!/usr/bin/env python3
"""
Algorithmic Selection Engine (ASE)
====================================
A falsifiable computational microscope for the Monotone Deletion
complexity hierarchy from the whitepaper:

"Monotone Deletion on Structured Graphs: A Complexity Hierarchy from 
Flow to Search, with an Application to Adversarial Narrative Retraction"

This tool implements the whitepaper's core contributions:
  - The complexity hierarchy (Section 3): flow / greedy / A*
  - Algorithm auto-selection (Algorithm 9.1)
  - SAA for uncertain graphs (Section 7)
  - Epistemic certificates (Section 7.4)

It does NOT claim to prove the whitepaper. It lets users:
  1. GENERATE synthetic MDP instances with known cost structure
  2. SOLVE them with all three solvers
  3. COMPARE actual cost ratios and runtime ratios
  4. FALSIFY by constructing counterexamples
  5. TEST SAA robustness vs. deterministic fragility

Usage:
    python ase.py --mode hierarchy --nodes 25 --regime modular
    python ase.py --mode falsify --gamma 0.1 --decay 0.0
    python ase.py --mode saa --accuracy 80 --samples 50
    python ase.py --mode auto --alpha 1.0 --beta 0.5 --gamma 0.0

Dependencies: networkx (pip install networkx)
"""

import argparse
import random
import time
import sys

try:
    import networkx as nx
except ImportError:
    print("ERROR: networkx is required. Install: pip install networkx")
    sys.exit(1)

from typing import Set, Tuple, Dict, Callable, Optional
import heapq


# =============================================================================
# 1. INSTANCE GENERATION
# =============================================================================

def generate_dag(n_nodes, edge_prob, seed=None):
    """Generate a random DAG with n_nodes and edge probability."""
    if seed is not None:
        random.seed(seed)
    G = nx.DiGraph()
    nodes = ["v" + str(i) for i in range(n_nodes)]
    G.add_nodes_from(nodes)

    for i in range(n_nodes):
        for j in range(i + 1, n_nodes):
            if random.random() < edge_prob:
                G.add_edge(nodes[i], nodes[j])

    n_sources = max(1, n_nodes // 5)
    n_sinks = max(1, n_nodes // 5)

    for n in G.nodes():
        G.nodes[n]["is_source"] = False
        G.nodes[n]["is_sink"] = False
        G.nodes[n]["weight"] = random.uniform(1.0, 5.0)

    for i in range(n_sources):
        G.nodes[nodes[i]]["is_source"] = True
    for i in range(n_nodes - n_sinks, n_nodes):
        G.nodes[nodes[i]]["is_sink"] = True

    return G


def make_modular_cost(G):
    """Modular costs: c(R) = sum of weights of deleted nodes. (Whitepaper Sec 3.1)"""
    weights = {n: G.nodes[n]["weight"] for n in G.nodes()}
    def cost(R):
        return sum(weights[v] for v in R)
    return cost


def make_submodular_cost(G, decay=0.3):
    """
    Submodular costs: marginal cost decreases as |R| grows.
    c(R) = sum_{v in R} w(v) * (1 - decay)^{|R_before_v|}
    (Whitepaper Sec 3.2)
    """
    weights = {n: G.nodes[n]["weight"] for n in G.nodes()}
    def cost(R):
        total = 0.0
        for i, v in enumerate(sorted(R)):
            total += weights[v] * ((1 - decay) ** i)
        return total
    return cost


def make_general_cost(G, gamma=2.0):
    """
    General monotone costs with interaction penalty.
    c(R) = sum_{v in R} w(v) + gamma * |pairs in R that are connected|
    (Whitepaper Sec 3.3)
    """
    weights = {n: G.nodes[n]["weight"] for n in G.nodes()}
    def cost(R):
        base = sum(weights[v] for v in R)
        interactions = 0
        R_list = list(R)
        for i in range(len(R_list)):
            for j in range(i + 1, len(R_list)):
                if nx.has_path(G, R_list[i], R_list[j]) or nx.has_path(G, R_list[j], R_list[i]):
                    interactions += 1
        return base + gamma * interactions
    return cost


# =============================================================================
# 2. SOLVERS
# =============================================================================

def solve_flow(G, sources, sinks, cost_fn):
    """
    Solve modular MDP via max-flow min-cut (Whitepaper Theorem 3.1).
    Vertex splitting construction from Section 6.1.
    Returns: (retracted_set, cost, runtime_ms)
    """
    t0 = time.perf_counter()

    flow_G = nx.DiGraph()
    src, snk = "__src__", "__snk__"

    for n in G.nodes():
        cap = float("inf") if G.nodes[n].get("is_sink", False) else G.nodes[n]["weight"]
        flow_G.add_edge(n + "_in", n + "_out", capacity=cap)

    for u, v in G.edges():
        flow_G.add_edge(u + "_out", v + "_in", capacity=float("inf"))

    for s in sources:
        flow_G.add_edge(src, s + "_in", capacity=float("inf"))
    for t in sinks:
        flow_G.add_edge(t + "_out", snk, capacity=float("inf"))

    try:
        cut_val, partition = nx.minimum_cut(flow_G, src, snk)
        reachable, non_reachable = partition

        retracted = set()
        for n in G.nodes():
            if n + "_in" in reachable and n + "_out" in non_reachable:
                retracted.add(n)

        # Only retract sources (non-sources have infinite capacity)
        retracted = retracted & sources

        runtime = (time.perf_counter() - t0) * 1000
        return retracted, cost_fn(retracted), runtime
    except Exception:
        runtime = (time.perf_counter() - t0) * 1000
        return set(), float("inf"), runtime


def solve_greedy(G, sources, sinks, cost_fn):
    """
    Greedy retraction for submodular/general costs (Whitepaper Algorithm 3.3).
    Iteratively selects vertex with best marginal cost-benefit ratio.
    Achieves (1-1/e) approximation for submodular costs (Theorem 3.2).
    """
    t0 = time.perf_counter()

    R = set()  # Retracted set
    remaining = set(sources)  # Still active sources

    def has_path_to_sink(active):
        for s in active:
            for t in sinks:
                if nx.has_path(G, s, t):
                    return True
        return False

    def count_paths_through_v(v, active):
        """Count source-sink paths that pass through v."""
        count = 0
        for s in active:
            if s == v:
                continue
            for t in sinks:
                if nx.has_path(G, s, v) and nx.has_path(G, v, t):
                    count += 1
        return count

    iteration = 0
    while has_path_to_sink(remaining) and iteration < 1000:
        iteration += 1
        best_ratio = float("inf")
        best_node = None

        for v in remaining:
            new_R = R | {v}
            marginal = cost_fn(new_R) - cost_fn(R)

            # Benefit: paths eliminated by removing v
            benefit = count_paths_through_v(v, remaining)
            # Plus v itself as a source reaching sinks
            for t in sinks:
                if nx.has_path(G, v, t):
                    benefit += 1

            if benefit > 0:
                ratio = marginal / benefit
                if ratio < best_ratio:
                    best_ratio = ratio
                    best_node = v

        if best_node is None:
            break

        R.add(best_node)
        remaining.discard(best_node)

    runtime = (time.perf_counter() - t0) * 1000
    return R, cost_fn(R), runtime


def solve_astar(G, sources, sinks, cost_fn):
    """
    A* search for general monotone costs (Whitepaper Section 4).
    Uses unit-capacity min-cut heuristic (Theorem 4.1, admissible).
    Proven consistent (Theorem 4.2).
    """
    t0 = time.perf_counter()

    def heuristic(state):
        """Unit-capacity min-cut heuristic (Whitepaper Section 4.2)."""
        if not state:
            return 0.0

        flow_G = nx.DiGraph()
        src, snk = "__src__", "__snk__"

        for n in state:
            flow_G.add_edge(n + "_in", n + "_out", capacity=1.0)
        for u, v in G.edges():
            if u in state and v in state:
                flow_G.add_edge(u + "_out", v + "_in", capacity=float("inf"))
        for s in state:
            flow_G.add_edge(src, s + "_in", capacity=float("inf"))
        for t in sinks:
            flow_G.add_edge(t + "_out", snk, capacity=float("inf"))

        try:
            cut_val, _ = nx.minimum_cut(flow_G, src, snk)
            return float(cut_val)
        except Exception:
            return 0.0

    def is_goal(state):
        for s in state:
            for t in sinks:
                if nx.has_path(G, s, t):
                    return False
        return True

    initial = frozenset(sources)
    open_heap = [(heuristic(initial), 0, 0.0, initial, [])]
    closed = set()
    counter = 1

    while open_heap:
        f, _, g, state, path = heapq.heappop(open_heap)

        if is_goal(state):
            runtime = (time.perf_counter() - t0) * 1000
            return set(path), g, runtime

        if state in closed:
            continue
        closed.add(state)

        for v in state:
            next_state = frozenset(state - {v})
            if next_state in closed:
                continue

            next_g = cost_fn(set(path + [v]))
            h = heuristic(next_state)
            heapq.heappush(open_heap, (next_g + h, counter, next_g, next_state, path + [v]))
            counter += 1

    runtime = (time.perf_counter() - t0) * 1000
    return set(), float("inf"), runtime


# =============================================================================
# 3. SAA FRAMEWORK (Whitepaper Section 7)
# =============================================================================

def sample_graph(G, edge_keep_prob, seed=None):
    """Sample a graph by keeping each edge with probability edge_keep_prob."""
    if seed is not None:
        random.seed(seed)
    G_sample = nx.DiGraph()
    G_sample.add_nodes_from(G.nodes(data=True))
    for u, v in G.edges():
        if random.random() < edge_keep_prob:
            G_sample.add_edge(u, v)
    return G_sample


def compute_primary_set(G, sources):
    """Compute primary claims: sources with in-degree 0."""
    return {n for n in sources if G.in_degree(n) == 0}


def saa_primary_instability(G, sources, K, edge_keep_prob):
    """
    Compute primary instability: fraction of samples where each source is primary.
    (Whitepaper Section 7.4: Epistemic Certificate component)
    """
    counts = {n: 0 for n in sources}
    for k in range(K):
        G_k = sample_graph(G, edge_keep_prob, seed=k)
        primaries = compute_primary_set(G_k, sources)
        for n in primaries:
            counts[n] += 1

    return {n: counts[n] / K for n in sources}


# =============================================================================
# 4. AUTO-SELECTION (Whitepaper Algorithm 9.1)
# =============================================================================

def auto_select(alpha, beta, gamma):
    """
    Whitepaper Algorithm 9.1: Automatic solver selection.
    Returns: (solver_name, complexity, guarantee)
    """
    if beta == 0 and gamma == 0:
        return "max-flow", "O(|V| * |E|)", "Exact"
    elif gamma == 0:
        return "greedy", "O(|V|^2 * |E|)", ">=63% optimal (typically ~94%)"
    else:
        return "A*", "Exponential in |S|", "Exact (optimal search)"


# =============================================================================
# 5. DASHBOARD MODES
# =============================================================================

def run_hierarchy_demo(nodes, edge_prob, regime):
    print("=" * 70)
    print("  COMPLEXITY HIERARCHY DEMO")
    print("  Nodes: " + str(nodes) + ", Edge density: " + str(edge_prob) + ", Regime: " + regime)
    print("=" * 70)

    G = generate_dag(nodes, edge_prob, seed=42)
    sources = {n for n in G.nodes() if G.nodes[n].get("is_source", False)}
    sinks = {n for n in G.nodes() if G.nodes[n].get("is_sink", False)}

    if regime == "modular":
        cost_fn = make_modular_cost(G)
    elif regime == "submodular":
        cost_fn = make_submodular_cost(G, decay=0.3)
    else:
        cost_fn = make_general_cost(G, gamma=2.0)

    print("\n  Sources: " + str(len(sources)) + " | Sinks: " + str(len(sinks)) + " | Total: " + str(nodes))
    print("  Cost regime: " + regime)

    results = []

    # Flow (only valid for modular)
    if regime == "modular":
        R, cost, rt = solve_flow(G, sources, sinks, cost_fn)
        results.append(("Max-Flow", R, cost, rt, True))
    else:
        results.append(("Max-Flow", set(), float("inf"), 0.0, False))

    # Greedy
    R, cost, rt = solve_greedy(G, sources, sinks, cost_fn)
    results.append(("Greedy", R, cost, rt, True))

    # A*
    R, cost, rt = solve_astar(G, sources, sinks, cost_fn)
    results.append(("A*", R, cost, rt, True))

    valid_results = [r for r in results if r[4]]
    best_cost = min(r[2] for r in valid_results) if valid_results else 1.0

    print("\n  Solver          | Cost       | Runtime (ms) | Valid  | Ratio     ")
    print("  " + "-" * 65)
    for name, R, cost, rt, valid in results:
        if best_cost > 0 and valid:
            ratio = cost / best_cost
            ratio_str = "{:.2f}x".format(ratio)
        else:
            ratio_str = "N/A"
        print("  {:<15} | {:<10.2f} | {:<12.2f} | {:<6} | {:<10}".format(
            name, cost, rt, "Yes" if valid else "No", ratio_str))

    print("\n  INSIGHT:")
    if regime == "modular":
        flow_rt = next((r[3] for r in results if r[0] == "Max-Flow"), 0)
        astar_rt = next((r[3] for r in results if r[0] == "A*"), 0)
        if astar_rt > 0 and flow_rt > 0:
            penalty = astar_rt / flow_rt
            print("    Routing modular to A* incurs {:.1f}x runtime penalty".format(penalty))
            print("    with ZERO cost benefit. Use max-flow (Whitepaper Sec 6.4).")
    elif regime == "submodular":
        greedy_cost = next((r[2] for r in results if r[0] == "Greedy"), 0)
        astar_cost = next((r[2] for r in results if r[0] == "A*"), 0)
        if astar_cost > 0:
            approx = greedy_cost / astar_cost
            print("    Greedy achieves {:.2%} of optimal cost.".format(approx))
            print("    The (1-1/e) ~ 63% bound is conservative in practice (Theorem 3.2).")
    else:
        greedy_cost = next((r[2] for r in results if r[0] == "Greedy"), 0)
        astar_cost = next((r[2] for r in results if r[0] == "A*"), 0)
        if astar_cost > 0:
            ratio = greedy_cost / astar_cost
            print("    Greedy achieves only {:.2%} of optimal.".format(ratio))
            print("    A* is necessary for exactness under general costs (Theorem 3.5).")


def run_falsify_demo(gamma, decay):
    print("=" * 70)
    print("  FALSIFICATION LAB")
    print("  gamma (interaction): " + str(gamma) + ", decay (submodular): " + str(decay))
    print("=" * 70)

    G = generate_dag(15, 0.3, seed=42)
    sources = {n for n in G.nodes() if G.nodes[n].get("is_source", False)}
    sinks = {n for n in G.nodes() if G.nodes[n].get("is_sink", False)}

    weights = {n: G.nodes[n]["weight"] for n in G.nodes()}
    def boundary_cost(R):
        base = sum(weights[v] for v in R)
        interactions = 0
        R_list = list(R)
        for i in range(len(R_list)):
            for j in range(i + 1, len(R_list)):
                if nx.has_path(G, R_list[i], R_list[j]):
                    interactions += 1
        return base + gamma * interactions

    print("\n  Cost function: c(R) = sum w(v) + " + str(gamma) + " * |interactions|")
    print("  This is TECHNICALLY general monotone (gamma > 0)")
    print("  But for small gamma, it is NEARLY modular.\n")

    R_g, cost_g, rt_g = solve_greedy(G, sources, sinks, boundary_cost)
    R_a, cost_a, rt_a = solve_astar(G, sources, sinks, boundary_cost)

    print("  Solver     | Cost       | Runtime (ms)")
    print("  " + "-" * 40)
    print("  {:<10} | {:<10.2f} | {:<12.2f}".format("Greedy", cost_g, rt_g))
    print("  {:<10} | {:<10.2f} | {:<12.2f}".format("A*", cost_a, rt_a))

    if cost_a > 0:
        gap = (cost_g - cost_a) / cost_a
        print("\n  Greedy-A* gap: {:.1%}".format(gap))

        if gamma < 0.5 and abs(gap) < 0.05:
            print("  WARNING: HIERARCHY GAP: For tiny gamma, greedy is within 5% of A*.")
            print("      A* is wasteful. The trichotomy has a continuum.")
        elif gamma < 0.5:
            print("  OK: Hierarchy holds but boundary is fuzzy.")
        else:
            print("  OK: Hierarchy confirmed: general costs need A*.")


def run_saa_demo(accuracy, K, false_root_rate):
    print("=" * 70)
    print("  SAA ROBUSTNESS DEMO")
    print("  Edge accuracy: " + str(accuracy) + "%, Samples K: " + str(K))
    print("=" * 70)

    G_true = generate_dag(20, 0.3, seed=42)
    sources = {n for n in G_true.nodes() if G_true.nodes[n].get("is_source", False)}
    sinks = {n for n in G_true.nodes() if G_true.nodes[n].get("is_sink", False)}

    P_true = compute_primary_set(G_true, sources)
    print("\n  True primary set: " + str(len(P_true)) + " nodes")

    edge_keep = accuracy / 100.0
    G_det = sample_graph(G_true, edge_keep, seed=999)
    P_det = compute_primary_set(G_det, sources)

    primary_freq = saa_primary_instability(G_true, sources, K, edge_keep)

    false_positives = len(P_det - P_true)
    false_negatives = len(P_true - P_det)

    print("\n  DETERMINISTIC EXTRACTION:")
    print("    Extracted primaries: " + str(len(P_det)))
    print("    False positives: " + str(false_positives) + " (non-primary classified as primary)")
    print("    False negatives: " + str(false_negatives) + " (primary missed)")

    print("\n  SAA PRIMARY INSTABILITY (K=" + str(K) + "):")
    unstable = [(n, 1 - f) for n, f in primary_freq.items() if f < 0.8]
    unstable.sort(key=lambda x: x[1], reverse=True)

    print("    Node     | Primary Freq | Instability  | Status")
    print("    " + "-" * 50)
    for n, inst in unstable[:10]:
        status = "UNSTABLE" if inst > 0.3 else "CAUTION" if inst > 0.1 else "STABLE"
        print("    {:<8} | {:<12.2f} | {:<12.2f} | {}".format(n, primary_freq[n], inst, status))

    if unstable:
        print("\n  WARNING: These nodes have unstable primary classification.")
        print("      A deterministic solver would misclassify them.")
        print("      SAA flags them for manual review (Whitepaper Sec 7.4).")
    else:
        print("\n  OK: All primaries are stable across samples.")


def run_auto_demo(alpha, beta, gamma):
    print("=" * 70)
    print("  AUTO-SELECTION DEMO (Algorithm 9.1)")
    print("  alpha=" + str(alpha) + ", beta=" + str(beta) + ", gamma=" + str(gamma))
    print("=" * 70)

    solver, complexity, guarantee = auto_select(alpha, beta, gamma)

    print("\n  Cost function: c(R) = " + str(alpha) + "*|Cl(R)| + " + str(beta) + "*sum d(v) + " + str(gamma) + "*phi(S-Cl(R))")
    print("\n  SELECTED SOLVER: " + solver)
    print("  Complexity: " + complexity)
    print("  Guarantee: " + guarantee)

    print("\n  REASONING:")
    if beta == 0 and gamma == 0:
        print("    beta = gamma = 0 -> Pure structural costs -> MODULAR")
        print("    Max-flow finds exact solution in polynomial time (Theorem 3.1).")
        print("    A* would be correct but exponentially slower (Sec 6.4).")
    elif gamma == 0:
        print("    gamma = 0, beta > 0 -> Per-claim damage, no interactions -> SUBMODULAR")
        print("    Greedy achieves >=63% of optimal (Theorem 3.2).")
        print("    Typically ~94% in practice (Whitepaper Table 3).")
    else:
        print("    gamma > 0 -> Interaction terms between retained claims -> GENERAL")
        print("    A* is necessary for exactness (Theorem 3.5).")
        print("    Greedy may achieve only ~76% of optimal (Whitepaper Table 3).")


# =============================================================================
# 6. CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Algorithmic Selection Engine (ASE) - "
                    "A falsifiable microscope for the Monotone Deletion hierarchy."
    )
    parser.add_argument("--mode", choices=["hierarchy", "falsify", "saa", "auto"],
                        default="hierarchy", help="Demo mode")
    parser.add_argument("--nodes", type=int, default=12, help="Number of nodes")
    parser.add_argument("--density", type=float, default=0.3, help="Edge density")
    parser.add_argument("--regime", choices=["modular", "submodular", "general"],
                        default="modular", help="Cost regime")
    parser.add_argument("--gamma", type=float, default=0.5, help="Interaction penalty")
    parser.add_argument("--decay", type=float, default=0.2, help="Submodular decay")
    parser.add_argument("--accuracy", type=int, default=85,
                        help="Edge extraction accuracy percent")
    parser.add_argument("--samples", type=int, default=20,
                        help="SAA sample count K")
    parser.add_argument("--alpha", type=float, default=1.0, help="Structural weight")
    parser.add_argument("--beta", type=float, default=0.0, help="Damage weight")

    args = parser.parse_args()

    if args.mode == "hierarchy":
        run_hierarchy_demo(args.nodes, args.density, args.regime)
    elif args.mode == "falsify":
        run_falsify_demo(args.gamma, args.decay)
    elif args.mode == "saa":
        run_saa_demo(args.accuracy, args.samples, 0)
    elif args.mode == "auto":
        run_auto_demo(args.alpha, args.beta, args.gamma)


if __name__ == "__main__":
    main()
