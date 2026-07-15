# Homotopic Hitting-Set A* (HHS-A*): High-Performance Exact Search for the Monotone Deletion Problem

## Abstract
The Homotopic Hitting-Set $A^*$ (HHS-A\*) algorithm is a high-performance search engine designed to solve the Monotone Deletion Problem (MDP) under the Root-Cut Paradigm (RCP). By combining static bitwise compilation, lexicographical symmetry breaking, and topological core-set heuristics, HHS-A\* resolves the two historic bottlenecks of guided graph search: **Permutation State-Space Aliasing** and **Heuristic Computation Overhead**. This paper provides a concise mathematical specification of the HHS-A\* primitives. For complete empirical datasets, historical debugging logs, and 50-seed Monte Carlo performance curves, the reader is referred to `RESEARCH_JOURNEY.md`.

---

## 1. Introduction & The Root-Cut Paradigm (RCP)

Let $G = (V, E_{\rightarrow} \cup E_{\dashv})$ be a directed graph containing deletable entailment edges $E_{\rightarrow}$ and unalterable contradiction edges $E_{\dashv}$ pointing to non-deletable sinks $\mathcal{T}$. Under the RCP, decisions are strictly constrained to the primary roots ($P \subseteq S$). A retraction set $R \subseteq P$ is valid if and only if no remaining active primary can reach a sink:

$$\text{Validity}(R) \equiv \left( (P \setminus R) \times \mathcal{T} \right) \cap \text{Paths}(G[V \setminus Cl(R)]) = \emptyset$$

Where $Cl(R)$ is the transitive closure of $R$ under $E_{\rightarrow}$. HHS-A\* is the high-performance execution engine designed to find the optimal retraction set minimizing a non-modular cost function $c(R)$.

---

## 2. The Three Algorithmic Pillars of HHS-A*

To outpace unguided uniform-cost search (Dijkstra) at scale, HHS-A\* implements three core optimizations:

### Pillar 1: Static Bitwise Compilation
To eradicate the microsecond-level CPU cycle overheads of runtime graph traversals, all topological dependencies are precomputed during a compiler initialization pass. 
*   **Node Representation:** All $N$ nodes are mapped to contiguous integers $0 \dots N-1$.
*   **Closures:** Every primary's closure $Cl(p_i)$ is stored as a 64-bit integer bitmask.
*   **Structural Cost:** The cost $g(Q)$ of a state is computed in $O(1)$ time using the hardware-level `popcount` (via Python's native `int.bit_count()`) of the bitwise OR of the retracted closure masks:
    $$g(R) = \text{popcount}\left( \bigvee_{r \in R} \text{closure\_mask}[r] \right)$$
*   **Validity Check:** The reachability of sinks is compiled into a single static primary vulnerability mask (`vul_mask`). Checking state validity is reduced to a single bitwise instruction:
    $$\text{is\_valid}(Q) \equiv (\text{active\_mask} \ \& \ \text{vul\_mask}) == 0$$

### Pillar 2: Lexicographical Symmetry Breaking (The 2-Cell Homotopy Collapse)
In a boolean hypercube, different permutation sequences to reach the same set of retractions (e.g., retracting $A$ then $B$ vs. $B$ then $A$) represent a 2-dimensional homotopy (a 2-cell). Because they share the same $f$-score, standard $A^*$ is forced to expand all $O(P!)$ permutations, causing exponential state-space aliasing.

HHS-A\* breaks this symmetry by enforcing a strict monotonic transition constraint:
$$\text{If primary } p_i \text{ is retracted at depth } d, \text{ successors at } d+1 \text{ can only retract } p_j \text{ where } j > i.$$

This collapses the multi-directional search hypercube into a strict, non-overlapping directed tree, ensuring that the closed-list (`visited` set) never encounters a duplicate path history.

### Pillar 3: The Disjoint Core-Set Theorem
To maintain mathematical admissibility ($h(Q) \le h^*(Q)$) over overlapping closures without running expensive runtime flow solvers on simple topologies, HHS-A\* precomputes the **Unique Topological Core** of each primary root:

$$\text{Core}(p) \equiv Cl(p) \setminus \bigcup_{q \in P \setminus \{p\}} Cl(q)$$

Because these core-sets are mutually disjoint by construction ($\text{Core}(u) \cap \text{Core}(v) = \emptyset$ for $u \neq v$), the sum of their cardinalities is a guaranteed lower bound on the size of the union of their closures:

$$h_{\text{core}}(Q) = \sum_{p \in \text{active\_vulnerable}(Q)} |\text{Core}(p)| \le \left| \bigcup_{p \in R_{\text{rem}}} Cl(p) \right|$$

This heuristic is computed in $O(P)$ bitwise operations, executing in nanoseconds. On disjoint topologies, it is perfectly exact ($h(Q) = h^*(Q)$), directing the search straight to the goal in exactly $d^*+1$ expansions.

---

## 3. The Dynamic Overlap Flow Heuristic

On highly overlapping graphs where unique cores shrink to $\emptyset$, HHS-A\* routes the heuristic calculation to our custom, array-backed **Edmonds-Karp Max-Flow Solver**.


```

[Active Graph G[Cl(Q)]]
                 │
     [Set Split Capacity of p_i] ──► Capacity = |Cl(p_i)| + Conflicts
                 │
                 ▼
      [Execute Edmonds-Karp] ──► Admissible Lower Bound h(Q)
```


1.  **Split-Node Construction:** It builds a flow network of the active remaining subgraph, setting the capacity of the primary split-edge $p_{\text{in}} \to p_{\text{out}}$ to its precomputed closure size $|Cl(p)|$, and intermediate nodes to $\infty$.
2.  **Dynamic Capacity Inflation:** To capture supermodular conflict penalties $W$ (paid when both $u$ and $v$ are retracted), the solver monitors the retraction history. If $u$ is already retracted and $v$ remains active, $v$'s split-edge capacity in the flow network is dynamically inflated by $W$:
    $$\text{Capacity}(v_{\text{in}} \to v_{\text{out}}) = |Cl(v)| + W$$
3.  **The Lower Bound:** The maximum s-t flow in this network computes the minimum structural and conflict cost required to sever the active paths, providing a highly informative, dynamic lower bound.

---

## 4. The Systems Crossover Contract

Because compiling and solving flow networks carries a real computational cost ($\approx 0.3\text{ ms}$ per node), HHS-A\* is a heavyweight instrument. Its use is governed by the **Crossover Inequality**:

$$1 + \frac{t_h}{t_s} < \frac{N_D}{N_A}$$

Where $t_h$ is the heuristic calculation time, $t_s$ is Dijkstra's bitwise transition time ($\approx 9\ \mu\text{s}$), $N_D$ is Dijkstra's expansion count, and $N_A$ is HHS-A\*'s expansion count. 

*   **For $|P| \le 14$:** Unguided Bitwise Dijkstra with Lexicographical Symmetry Breaking is almost always faster in raw wall-clock time due to near-zero per-node overhead.
*   **For $|P| \ge 20$:** Dijkstra enters its binomial state explosion, and HHS-A\*'s pruning ratio secures an exponential wall-clock speedup.

For the raw empirical transition logs, the 50-seed Monte Carlo dataset, and the complete systems profiling of these crossover boundaries, see `RESEARCH_JOURNEY.md`.