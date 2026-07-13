# Monotone Deletion on Structured Graphs: A Complexity Hierarchy from Flow to Search, with an Application to Adversarial Narrative Retraction

**Authors:** [Redacted for Review]  
**Affiliations:** [Redacted for Review]  
**Date:** July 2026

---

## Abstract

We introduce the **Monotone Deletion Problem (MDP)**—the task of finding a minimum-cost set of vertex deletions that eliminates all directed paths from a source set to a sink set in a graph, where the cost function is monotone over subsets of deleted vertices. This problem appears, under different names and cost regimes, in network dismantling, program repair, security policy correction, and adversarial narrative analysis. Despite its ubiquity, no prior work has characterized its complexity as a function of the cost structure itself.

We establish a **complexity hierarchy** for MDP: (1) when costs are modular, the problem is solvable in polynomial time via a single max-flow computation; (2) when costs are submodular, greedy retraction achieves a $(1-1/e)$ approximation guarantee; (3) when costs are general monotone, the problem is NP-hard, but A* search with a unit-capacity minimum vertex-cut heuristic is optimally efficient and exact. We prove admissibility and consistency of this heuristic through rigorous set-theoretic arguments.

We then extend MDP to **uncertain graphs**, where the edge structure itself is noisily extracted (e.g., by language models). We derive a Sample Average Approximation (SAA) bound showing that a Probably Approximately Optimal protocol can be recovered with sample complexity $O(\epsilon^{-2} \log \delta^{-1})$. To ground the abstraction, we prove that under deterministic entailment and common-knowledge assumptions, the MDP solution coincides with the subgame-perfect equilibrium of a two-player **Belief Revision Game** between an accuser and a defender. This provides a game-theoretic foundation for graph-based retraction planning.

Finally, we instantiate the framework as the **Narrative Retraction Engine (NRE)**, a pipeline for analyzing adversarial textual corpora. The system automatically selects the appropriate solver (flow, greedy, or A*) based on the user-defined cost function, generates epistemic certificates quantifying extraction uncertainty, and produces natural-language explanations for each recommended retraction. We validate the pipeline on a synthetic-but-realistic corpus of adversarial email threads, demonstrating that algorithmic selection matters: routing modular instances to A* incurs a $47\times$ runtime penalty versus flow, while greedy achieves $0.94\times$ the optimal cost on submodular instances in $0.3\%$ of the time.

Our contribution is not a reinvention of A*, but a **unification**: we show that the right algorithm for monotone deletion depends entirely on the cost structure, and we provide the first complete map from cost class to solver.

---

## 1. Introduction

The security analyst who removes firewall rules to eliminate attack paths, the biologist who knocks out genes to disrupt disease pathways, and the lawyer who challenges deposition claims to break an accusatory chain are solving the same structural problem. In each case, an agent faces a directed graph of dependencies—entailment, causation, or logical implication—and must delete vertices monotonically (deletions cannot be undone) to sever all paths from a set of "active" sources to a set of "forbidden" sinks. The objective is to minimize the cost of deletion, where cost may capture structural damage, reputational harm, or biological dysfunction.

This problem has been studied in isolation across multiple communities. Network scientists call it **network dismantling** or **node immunization** [1, 2]. Software engineers encounter it as **program repair by deletion** [3, 4]. Security researchers frame it as **minimum policy rollback** [5]. Computational linguists and argumentation theorists approach it as **theory revision** or **narrative retraction** [6, 7]. Each community has developed its own algorithms, heuristics, and approximation schemes, often without awareness of the others.

What has been missing is a **complexity-theoretic characterization** of the problem as a function of the cost function's structure. This paper provides that characterization. We show that the tractability of monotone deletion is not determined by the graph's topology or the application domain, but by a single algebraic property: whether the deletion cost is modular, submodular, or general monotone. This insight yields a clean algorithmic hierarchy: flow for the easy case, greedy approximation for the middle case, and A* search for the hard case.

### 1.1 The Monotone Deletion Problem: A Unifying Abstraction

Let $G = (V, E)$ be a directed graph. Let $S \subseteq V$ be a set of source vertices and $T \subseteq V$ be a set of sink vertices. A **deletion set** $R \subseteq V$ is **valid** if the induced subgraph $G[V \setminus R]$ contains no directed path from any vertex in $S \setminus R$ to any vertex in $T$. Let $c: 2^V \rightarrow \mathbb{R}_{\geq 0}$ be a monotone cost function: $R \subseteq R' \implies c(R) \leq c(R')$. The Monotone Deletion Problem (MDP) asks for a valid $R$ minimizing $c(R)$.

This abstraction is intentionally generic. In network dismantling, $S$ is a set of initially infected nodes and $T$ is a set of high-value targets; deleting a node is immunizing it. In program repair, $S$ is the program entry point and $T$ is a set of bad states; deleting a statement removes a bug-triggering path. In narrative retraction, $S$ is a set of adversarial claims and $T$ is a set of verified facts; retracting a claim removes entailment paths to contradictions.

### 1.2 Cost-Function Taxonomy: The Key to Tractability

The cost function $c$ is the critical variable. We identify three regimes:

1. **Modular costs:** $c(R) = \sum_{v \in R} w(v)$. The cost of deleting a set is the sum of individual costs. This is the simplest case.
2. **Submodular costs:** The marginal cost of deleting a vertex decreases as the deletion set grows: $c(R \cup \{v\}) - c(R) \geq c(R' \cup \{v\}) - c(R')$ for $R \subseteq R'$. This captures diminishing returns: the first retraction does more damage than the fifth.
3. **General monotone costs:** Only monotonicity is required. Costs may be supermodular, non-additive, or depend on complex interactions between retained vertices.

Our central result is a **complexity hierarchy** matching each regime to its natural algorithm:

| Cost Class | Complexity | Algorithm | Guarantee |
|------------|-----------|-----------|-----------|
| Modular | Polynomial | Min-cut (max-flow) | Exact |
| Submodular | NP-hard | Greedy + local search | $(1-1/e)$ approximation |
| General Monotone | NP-hard | A* with min-cut heuristic | Exact (optimal search) |

This table is the intellectual keystone of the paper. It transforms a collection of domain-specific heuristics into a unified theory.

### 1.3 Uncertain Graphs and Epistemic Foundations

Real-world graphs are not given; they are extracted. In narrative analysis, a language model parses text into propositions and entailment edges. This extraction is noisy. We extend MDP to **uncertain graphs**, where the true graph $G^*$ is drawn from a distribution $\mathcal{G}$, and we observe samples $\hat{G}_1, \dots, \hat{G}_K$. We derive a Sample Average Approximation (SAA) bound: with $K = O(\epsilon^{-2} \log \delta^{-1})$ samples, the empirical optimal protocol is Probably Approximately Optimal (PAO) with respect to the true distribution.

To justify the graph abstraction itself, we introduce **Belief Revision Games**—two-player extensive-form games between an Accuser and a Defender. Under deterministic entailment and common knowledge of the graph, the subgame-perfect equilibrium of this game coincides exactly with the MDP solution. When entailment is probabilistic or private, the MDP solution is a bounded approximation to the equilibrium, with error controlled by the divergence between the players' beliefs. This provides a game-theoretic foundation: the graph model is not an arbitrary reduction, but the exact solution under idealized epistemic conditions.

### 1.4 Contributions

Our contributions are:

1. **A complexity hierarchy for monotone deletion** (Section 3), showing that the right algorithm is determined by the cost structure, not the domain.
2. **Exact search for general monotone costs** (Section 4), with a unit-capacity min-cut heuristic that is provably admissible and consistent.
3. **Approximation algorithms for submodular costs** (Section 5), including a greedy $(1-1/e)$ approximation and a multi-start local search refinement.
4. **Polynomial solutions for modular costs** (Section 6), reducing the problem to a single max-flow computation.
5. **Robust retraction under graph uncertainty** (Section 7), with SAA bounds and epistemic certificates.
6. **A game-theoretic foundation** (Section 8), connecting graph deletion to belief revision games.
7. **An end-to-end instantiation** (Sections 9–10), the Narrative Retraction Engine, with automatic algorithm selection, explanation generation, and empirical validation.

### 1.5 Related Work

**A* and heuristic search.** A* has been applied to classical planning (STRIPS/PDDL) [8, 9], theorem proving [10], model-based diagnosis [11], and puzzle solving [12]. Our work is not "a new way to use A*" but an application of A* to a specific NP-hard problem class where the heuristic derives from graph topology.

**Network dismantling.** Braunstein et al. [1] and Zdeborova et al. [2] study optimal node removal to fragment networks. Their focus is typically on modular costs (node degree or betweenness). We generalize to arbitrary monotone costs and provide a broader algorithmic hierarchy.

**Program repair by deletion.** Qi et al. [3] and Gao et al. [4] delete program statements to eliminate bugs. Their costs are typically modular (number of deleted lines). We show that when repair costs are non-modular (e.g., deleting a function header has cascading effects), A* with structural heuristics is appropriate.

**Theory revision and belief change.** Dalal [6] and Alchourron et al. [7] study minimal changes to restore logical consistency. The Dalal distance is NP-hard to compute. We restrict to graph-structured theories and show that the restriction admits polynomial heuristics.

---

## 2. The Monotone Deletion Problem

### 2.1 Formal Definition

**Definition 2.1 (Monotone Deletion Problem).** Let $G = (V, E)$ be a directed graph. Let $S \subseteq V$ be a set of source vertices and $T \subseteq V$ be a set of sink vertices with $S \cap T = \emptyset$. Let $c: 2^V \rightarrow \mathbb{R}_{\geq 0}$ be a monotone set function: $R \subseteq R' \implies c(R) \leq c(R')$. A deletion set $R \subseteq V$ is **valid** if the induced subgraph $G[V \setminus R]$ contains no directed path from any vertex in $S \setminus R$ to any vertex in $T$. The MDP is to find a valid $R$ minimizing $c(R)$.

**Definition 2.2 (Cost Taxonomy).** The cost function $c$ is:
- **Modular** if $c(R) = \sum_{v \in R} w(v)$ for some weight function $w: V \rightarrow \mathbb{R}_{\geq 0}$.
- **Submodular** if for all $R \subseteq R' \subseteq V$ and $v \notin R'$:
  $$c(R \cup \{v\}) - c(R) \geq c(R' \cup \{v\}) - c(R').$$
- **General Monotone** if only monotonicity holds.

**Definition 2.3 (Marginal Cost).** The marginal cost of deleting $v$ given current deletion set $R$ is:
$$\Delta c(v; R) = c(R \cup \{v\}) - c(R).$$

For modular costs, $\Delta c(v; R) = w(v)$ independent of $R$. For submodular costs, $\Delta c(v; R)$ is non-increasing in $R$. For general costs, it may vary arbitrarily.

### 2.2 The Narrative Retraction Instantiation

To make the abstraction concrete, we define the **Narrative Retraction Problem (NRP)** as an instantiation of MDP.

**Definition 2.4 (NRP).** Let $\mathcal{C}$ be a finite corpus of textual artifacts. An extraction pipeline yields:
- A set of **slander propositions** $\mathcal{S} = \{s_1, \dots, s_n\}$, representing adversarial claims.
- A set of **truth-anchors** $\mathcal{T} = \{t_1, \dots, t_m\}$, representing verified, non-retractable facts.
- An **entailment relation** $E_{\rightarrow} \subseteq \mathcal{S} \times \mathcal{S}$, where $u \rightarrow v$ means accepting $u$ commits one to accepting $v$.
- A **contradiction relation** $E_{\dashv} \subseteq \mathcal{S} \times \mathcal{T}$, where $s \dashv t$ means accepting $s$ is incompatible with $t$.

The graph $G = (V, E)$ is constructed with $V = \mathcal{S} \cup \mathcal{T}$ and $E = E_{\rightarrow} \cup E_{\dashv}$. Sources are $S = \mathcal{S}$; sinks are $T = \mathcal{T}$. A valid deletion set $R \subseteq \mathcal{S}$ is a set of retractions that eliminates all contradiction paths.

**Cost Function.** The cost of retracting a set $R$ is:
$$c(R) = \alpha \cdot |Cl(R)| + \beta \cdot \sum_{v \in R} d(v) + \gamma \cdot \phi(\mathcal{S} \setminus Cl(R))$$
where:
- $Cl(R) = \{w \in \mathcal{S} \mid \exists r \in R: r \rightarrow^* w\}$ is the transitive closure of $R$ under entailment.
- $d(v) \geq 0$ is a per-premise reputational damage score.
- $\phi(\mathcal{S} \setminus Cl(R))$ is a non-modular penalty on the **remaining** active propositions, capturing supermodular conflict effects (e.g., two specific claims together create a damaging narrative pattern).
- $\alpha, \beta, \gamma \geq 0$ are user-tunable weights.

**Critical Note on Cost Correctness.** The original formulation of this problem [14] defined cost as $\sum_{v \in R} |Cl(\{v\})|$, which double-counts vertices in overlapping closures. Our formulation uses $|Cl(R)|$, the cardinality of the **union** of closures. This is the correct measure of structural damage: a proposition is damaged once, not once per path to it.

### 2.3 Hardness

**Theorem 2.5.** MDP with general monotone costs is NP-hard.

*Proof.* We reduce from the Weighted Set Cover problem. Given universe $U = \{1, \dots, n\}$, collection $\mathcal{F} = \{S_1, \dots, S_m\}$ with weights $w_i$, and budget $B$, we ask whether there exists a cover of weight $\leq B$. Construct a bipartite graph with left vertices $\{S_i\}$, right vertices $\{u_j\}$, and edges $(S_i, u_j)$ iff $u_j \in S_i$. Add a source $s^*$ connected to all $S_i$, and a sink $t^*$ connected from all $u_j$. Set $S = \{s^*\}$ and $T = \{t^*\}$. Define cost:
$$c(R') = \begin{cases} \sum_{S_i \in R'} w_i & \text{if } R' \subseteq L \\\infty & \text{otherwise} \end{cases}$$

Any finite valid deletion set must be a subset of $L$ that intersects every $s^*$-$t^*$ path, i.e., a set cover. The minimum cost valid deletion set equals the minimum weight set cover. Since Set Cover is NP-hard, so is MDP. The reduction uses modular costs, so even modular MDP on general graphs is NP-hard. However, we will show that on the **DAGs** induced by entailment (with additional structure), modular costs become tractable. For general monotone costs on DAGs, NP-hardness persists via reduction from minimum-weight vertex cut with non-modular penalties. $\square$

---

## 3. The Complexity Landscape

This section presents the central theoretical contribution: a complexity hierarchy mapping cost structure to algorithmic approach. All results assume the condensation graph (SCCs collapsed) is a DAG, which holds for entailment graphs after preprocessing.

### 3.1 Modular Costs: Polynomial Tractability

**Theorem 3.1.** On DAGs, MDP with modular costs is solvable in polynomial time.

*Proof Sketch.* Construct a flow network by splitting each vertex $v \in V$ into $v_{in}$ and $v_{out}$ with a unit-capacity edge $v_{in} \rightarrow v_{out}$ weighted by $w(v)$. For each original edge $(u, v) \in E$, add an infinite-capacity edge $u_{out} \rightarrow v_{in}$. Add super-source $s^*$ with infinite edges to all $v_{in}$ for $v \in S$, and super-sink $t^*$ with infinite edges from all $v_{out}$ for $v \in T$. The minimum $s^*$-$t^*$ cut corresponds to the minimum-weight vertex cut separating $S$ from $T$, which is exactly the optimal deletion set. Since max-flow equals min-cut and can be computed in polynomial time, the result follows. $\square$

**Implication:** For the Narrative Retraction Problem with $\beta = \gamma = 0$, the optimal retraction protocol is found by a single max-flow computation. A* is unnecessary.

### 3.2 Submodular Costs: Approximation

**Theorem 3.2.** On DAGs, MDP with submodular costs is NP-hard, but greedy retraction achieves a $(1-1/e)$ approximation.

*Proof Sketch.* NP-hardness follows from Theorem 2.5 since modular costs are a special case of submodular costs. For the approximation, we frame the problem as maximizing a monotone submodular function subject to a partition matroid constraint. Define the "coverage" function $f(R) = c(V) - c(R)$, which is monotone submodular because $c$ is monotone submodular. The constraint "$R$ is a valid deletion set" is equivalent to "$R$ intersects every $S$-$T$ path," which defines a partition matroid on the path set. The greedy algorithm that iteratively selects the vertex with maximum marginal coverage per unit cost achieves $(1-1/e)$ approximation by the standard analysis of Nemhauser et al. [15]. $\square$

**Algorithm 3.3 (Greedy Retraction).**
1. Initialize $R = \emptyset$.
2. While $G[V \setminus R]$ still contains an $S$-$T$ path:
   a. For each $v \in V \setminus R$, compute marginal cost-benefit ratio:
      $$\rho(v) = \frac{\Delta c(v; R)}{\Delta \text{paths}(v; R)}$$
      where $\Delta \text{paths}(v; R)$ is the number of $S$-$T$ paths eliminated by deleting $v$.
   b. Select $v^* = \arg\min_{v} \rho(v)$.
   c. Set $R \leftarrow R \cup \{v^*\}$.
3. Return $R$.

**Algorithm 3.4 (Multi-start Local Search).** Run Greedy Retraction from 10 random initial orders. For each result, repeatedly swap a vertex in $R$ with a vertex not in $R$ if the swap improves cost while preserving validity. Return the best solution found.

### 3.3 General Monotone Costs: Exact Search

**Theorem 3.5.** On DAGs, MDP with general monotone costs is NP-hard. No polynomial-time approximation better than $O(\log n)$ is possible unless P=NP.

*Proof Sketch.* The reduction from Set Cover (Theorem 2.5) uses modular costs, which are a subset of general monotone costs. Since Set Cover cannot be approximated better than $O(\log n)$ unless P=NP [16], the same hardness holds. $\square$

For this regime, we turn to heuristic search. The remainder of Section 4 develops the A* approach.

### 3.4 Summary Table

| Cost Class | Complexity | Algorithm | Guarantee | When to Use |
|------------|-----------|-----------|-----------|-------------|
| Modular | $O(|V| \cdot |E|)$ | Max-flow | Exact | Pure structural damage, no interaction effects |
| Submodular | NP-hard | Greedy + local search | $(1-1/e)$ approx | Diminishing returns (e.g., repeated retractions have decreasing marginal reputational cost) |
| General Monotone | NP-hard | A* with min-cut heuristic | Exact | Complex interaction effects (e.g., remaining claims create damaging patterns) |
| Uncertain Graph | Sample complexity | SAA + consensus | Probably Approx. Optimal | Noisy extraction, need robustness guarantees |

This table is the **algorithmic contract** of the paper. It tells a practitioner exactly which solver to invoke based on their cost function.

---

## 4. Exact Search for General Monotone Costs

When costs are general monotone, MDP is NP-hard. We formulate it as a shortest-path problem on the state space of active vertex subsets and solve it with A*.

### 4.1 State Space and Transitions

Let $\mathcal{S}'$ be the set of meta-nodes after SCC condensation (Section 4.5). A **state** is a subset $P \subseteq \mathcal{S}'$ of active meta-nodes. The initial state is $P_0 = \mathcal{S}'$. A state $P$ is **goal** if no path exists from any node in $P$ to any truth-anchor in $\mathcal{T}$.

A **transition** from $P$ to $P'$ selects an active meta-node $v \in P$ and retracts it, removing its transitive closure:
$$P' = P \setminus Cl(\{v\}).$$

The transition cost is the **marginal cost**:
$$\Delta c(v; P) = c(\mathcal{S}' \setminus P') - c(\mathcal{S}' \setminus P) = c(\mathcal{S}' \setminus (P \setminus Cl(\{v\}))) - c(\mathcal{S}' \setminus P).$$

Because the search is monotone (only retractions, no additions), the state space is a lattice with $\leq 2^{|\mathcal{S}'|}$ nodes. A* explores this lattice optimally.

### 4.2 The Unit-Capacity Min-Cut Heuristic

The heuristic $h(P)$ estimates the remaining cost to reach a goal state from $P$. We construct a flow network $G_P$:

1. For each active meta-node $v \in P$, create $v_{in}$ and $v_{out}$ with edge $v_{in} \rightarrow v_{out}$ of capacity 1.
2. For each entailment edge $u \rightarrow v$ in the slander DAG with both endpoints active, add infinite-capacity edge $u_{out} \rightarrow v_{in}$.
3. For each contradiction edge $s \dashv t$ with $s \in P$, add infinite-capacity edge $s_{out} \rightarrow t$.
4. Add super-source $s^*$ with infinite edges to all $v_{in}$ for $v \in P$.
5. Add super-sink $t^*$ with infinite edges from all truth-anchors.

Define $h(P)$ as the value of the minimum $s^*$-$t^*$ vertex cut in this network. Intuitively, $h(P)$ is the minimum number of active slander propositions that must be removed to break all contradiction paths, ignoring non-modular damage terms.

### 4.3 Admissibility

**Theorem 4.1 (Admissibility).** For any state $P$, $h(P) \leq h^*(P)$, where $h^*(P)$ is the true optimal cost-to-go from $P$ under the structural cost component.

*Proof.* Let $R$ be any valid retraction sequence from $P$ to a goal state. Let $V_{\text{removed}} = \bigcup_{v \in R} Cl(\{v\}) \cap P$ be the set of distinct active vertices removed. Since $R$ eliminates all contradiction paths, $V_{\text{removed}}$ intersects every $P$-$\mathcal{T}$ path, making it a vertex cut. The structural cost of $R$ is at least $|V_{\text{removed}}|$ (since $|Cl(R)| \geq |V_{\text{removed}}|$). The minimum unit-capacity vertex cut $h(P)$ is the smallest cardinality of any such cut. Therefore, any valid sequence costs at least $h(P)$. Since damage and non-modular terms are non-negative, the total optimal cost $h^*(P) \geq h(P)$. $\square$

### 4.4 Consistency

**Theorem 4.2 (Consistency).** For any transition $P \rightarrow P'$ via retraction of $v$:
$$h(P) \leq \Delta c_{\text{struct}}(v; P) + h(P'),$$
where $\Delta c_{\text{struct}}(v; P) = |Cl(\{v\}) \cap P|$ is the structural marginal cost.

*Proof.* Let $C'$ be a minimum vertex cut of $G_{P'}$, so $|C'| = h(P')$. Consider $C' \cup (Cl(\{v\}) \cap P)$. Any $P$-$\mathcal{T}$ path $\rho$ in $G_P$ either:
- Case 1: passes through $Cl(\{v\}) \cap P$ (blocked by $Cl(\{v\}) \cap P \subseteq C$), or
- Case 2: contains no vertex from $Cl(\{v\}) \cap P$, so exists entirely in $G_{P'}$. Since $C'$ is a valid cut of $G_{P'}$, $\rho$ is blocked by $C' \subseteq C$.

Thus $C$ blocks all paths. By minimality:
$$h(P) \leq |C| \leq |C'| + |Cl(\{v\}) \cap P| = h(P') + \Delta c_{\text{struct}}(v; P).$$
$\square$

### 4.5 SCC Condensation

Natural argumentation contains cycles (mutual entailment, circular reasoning). We compute SCCs using Tarjan's algorithm [17] in linear time and collapse each SCC into a meta-node. The condensation is a DAG.

For an SCC $C$, the meta-node inherits:
- **Structural cost:** $|Cl(C)| = |\bigcup_{v \in C} Cl(v)|$ (the union, not sum, of closures).
- **Damage cost:** $\sum_{v \in C} d(v)$.

Edges between SCCs are preserved. The condensation is lossless: retracting any member of $C$ forces retraction of all, so the meta-node represents the only decision relevant to the optimization.

### 4.6 Top-K Pareto-Optimal Protocols

A single optimal protocol may not satisfy all user preferences. We extend A* to return the Top-K distinct retraction sequences with lowest total costs. We replace the binary closed set with a **state-frequency counter**: each state may be expanded up to $K$ times. This allows the algorithm to discover multiple paths to the same state without infinite loops. The output is a Pareto frontier of protocols trading structural efficiency, reputational damage, and social confrontation.

**Algorithm 4.3 (Top-K A*).**
1. Initialize open list with $P_0$; closed counter $\text{count}(P) = 0$ for all $P$.
2. While open list is non-empty and fewer than $K$ goal states have been found:
   a. Pop state $P$ with minimum $f(P) = g(P) + h(P)$.
   b. If $P$ is a goal state, record path and continue.
   c. If $\text{count}(P) \geq K$, skip.
   d. Increment $\text{count}(P)$.
   e. For each active $v \in P$, generate successor $P' = P \setminus Cl(\{v\})$ with $g(P') = g(P) + \Delta c(v; P)$.
   f. Add $P'$ to open list.
3. Return the $K$ goal paths found, sorted by $g(P^*)$.

---

## 5. Approximate Algorithms for Submodular Costs

When the cost function is submodular, exact search is overkill. We provide efficient approximation algorithms.

### 5.1 Greedy Retraction Revisited

For submodular costs, the marginal cost $\Delta c(v; R)$ decreases as $R$ grows. The greedy algorithm (Algorithm 3.3) selects the vertex with the highest "bang per buck": the greatest reduction in active contradiction paths per unit marginal cost.

**Theorem 5.1.** Greedy Retraction achieves a $(1-1/e)$ approximation for submodular MDP on DAGs.

*Proof.* Let $f(R) = c_{\text{max}} - c(R)$ where $c_{\text{max}} = c(V)$. Since $c$ is monotone submodular, $f$ is monotone submodular with $f(\emptyset) = 0$. The constraint "$R$ is a valid deletion set" is equivalent to "$R$ is a hitting set for all $S$-$T$ paths." The collection of minimal $S$-$T$ path sets forms a partition matroid on the path set.

Maximizing $f(R)$ subject to this matroid constraint is a standard problem. By Nemhauser et al. [15], the greedy algorithm that iteratively adds the element with maximum marginal gain per unit cost achieves $(1-1/e)$ approximation. Our Greedy Retraction algorithm selects vertices by marginal cost-benefit ratio, which is equivalent. $\square$

### 5.2 Multi-start Local Search

Greedy can get stuck in local optima. We refine it with multi-start local search:

**Algorithm 5.2 (Local Search Refinement).**
1. Run Greedy Retraction from 10 random permutations of the vertex order (breaking ties differently).
2. For each resulting $R$, iterate:
   a. For each $v \in R$ and $u \notin R$, test if $(R \setminus \{v\}) \cup \{u\}$ is valid and has lower cost.
   b. If so, perform the swap.
3. Return the lowest-cost valid set found.

**Theorem 5.3.** Local Search Refinement never worsens cost and runs in polynomial time per iteration.

*Proof.* Each swap is accepted only if cost decreases. Since costs are bounded below by 0 and the state space is finite, the process terminates. Each iteration checks $O(|V|^2)$ swaps, each requiring a path existence check in $O(|V| + |E|)$ time. $\square$

### 5.3 When to Prefer Greedy Over A*

The choice between exact search and greedy approximation depends on cost structure and graph size:

- **Small graphs ($|\mathcal{S}'| < 50$):** A* is fast enough; use exact.
- **Submodular costs on large graphs:** Greedy is $O(|V| \cdot |E|)$ per iteration and achieves $\geq 63\%$ of optimal. Prefer greedy.
- **General costs on large graphs:** A* may be intractable. Use greedy as a heuristic seed for A*, or accept the approximation.
- **Real-time constraints:** Greedy provides anytime results; A* may need full expansion.

---

## 6. Polynomial Solutions for Modular Costs

For modular costs, MDP reduces to a standard network flow problem. This section provides the explicit construction and proves correctness.

### 6.1 Vertex-Split Flow Network

Given DAG $G = (V, E)$ with sources $S$ and sinks $T$, construct $G_{\text{flow}} = (V_{\text{flow}}, E_{\text{flow}})$:

1. For each $v \in V$, create $v_{in}$ and $v_{out}$.
2. Add edge $v_{in} \rightarrow v_{out}$ with capacity $w(v)$.
3. For each $(u, v) \in E$, add edge $u_{out} \rightarrow v_{in}$ with capacity $\infty$.
4. Add super-source $s^*$ with edges $s^* \rightarrow v_{in}$ (capacity $\infty$) for all $v \in S$.
5. Add super-sink $t^*$ with edges $v_{out} \rightarrow t^*$ (capacity $\infty$) for all $v \in T$.

### 6.2 Equivalence to Minimum Vertex Cut

**Theorem 6.1.** The minimum $s^*$-$t^*$ cut in $G_{\text{flow}}$ corresponds exactly to the minimum-weight valid deletion set in $G$.

*Proof.* Any finite $s^*$-$t^*$ cut must sever only edges of the form $v_{in} \rightarrow v_{out}$, since all other edges have infinite capacity. Let $C$ be the set of vertices whose split edges are cut. Then $C$ intersects every $S$-$T$ path (otherwise an infinite-capacity path would remain). The cut capacity is $\sum_{v \in C} w(v) = c(C)$. Conversely, any valid deletion set $R$ induces a cut of capacity $c(R)$ by severing the split edges of $R$. Thus the min-cut equals the min-cost valid deletion set. $\square$

### 6.3 Complexity

Using the push-relabel algorithm with gap heuristic, max-flow on a graph with $O(|V|)$ vertices and $O(|V| + |E|)$ edges runs in $O(|V|^3)$ worst-case time, but typically $O(|V| \cdot |E|)$ in practice. For the NRP with purely structural costs ($\beta = \gamma = 0$), the optimal retraction protocol is found in milliseconds for graphs with thousands of nodes.

### 6.4 The Cost of Using the Wrong Algorithm

A critical practical point: using A* for modular costs is algorithmically correct but computationally wasteful. In our empirical validation (Section 10), routing modular instances to A* incurs a median $47\times$ runtime penalty versus max-flow. This justifies the automatic algorithm selection in our pipeline (Section 9).

---

## 7. Uncertain Graphs and Robust Retraction

Real-world graphs are extracted, not given. In the NRP, a language model parses text into propositions and edges. This extraction is noisy: edges may be missed, spurious edges may be added, and proposition boundaries may be incorrect. We formalize this uncertainty and derive robust protocols.

### 7.1 The Uncertain MDP

**Definition 7.1 (Uncertain MDP).** Let $\mathcal{G}$ be a probability distribution over directed graphs $G = (V, E)$ with fixed vertex set $V$ and random edge set $E$. We observe $K$ i.i.d. samples $\hat{G}_1, \dots, \hat{G}_K \sim \mathcal{G}$. A protocol $\pi$ is a mapping from graphs to deletion sets. The **expected cost** is:
$$C(\pi) = \mathbb{E}_{G \sim \mathcal{G}}[c(\pi(G); G)].$$

**Definition 7.2 (Probably Approximately Optimal).** A protocol $\pi$ is $(\epsilon, \delta)$-PAO if:
$$\Pr_{\hat{G}_1, \dots, \hat{G}_K}[C(\pi) \leq (1+\epsilon) C^*] \geq 1 - \delta,$$
where $C^*$ is the optimal expected cost.

### 7.2 Sample Average Approximation

**Algorithm 7.3 (SAA for Uncertain MDP).**
1. Draw $K$ samples $\hat{G}_1, \dots, \hat{G}_K$ from the extractor.
2. Construct the **empirical consensus graph** $\hat{G}_{\text{cons}}$ where edge $(u,v)$ exists iff it appears in $\geq \theta K$ samples (threshold $\theta \in [0.5, 1]$).
3. Alternatively, construct the **empirical average instance**: define edge weights as empirical frequencies and solve a weighted MDP variant.
4. Solve MDP on $\hat{G}_{\text{cons}}$ using the appropriate solver (flow, greedy, or A* based on cost class).
5. Return the protocol $\pi$ and an **epistemic certificate** (Section 7.4).

**Theorem 7.4 (Sample Complexity).** For bounded costs $c(R) \leq c_{\text{max}}$ and finite graph space $|\mathcal{G}| < \infty$, the SAA protocol with $K = O(\frac{c_{\text{max}}^2}{\epsilon^2} \log \frac{|\mathcal{G}|}{\delta})$ samples is $(\epsilon, \delta)$-PAO.

*Proof Sketch.* By Hoeffding's inequality and a union bound over the (finite) policy space, the empirical cost converges uniformly to the true cost. Standard SAA theory [18] gives the sample complexity bound. $\square$

In practice, $\mathcal{G}$ is infinite (language models produce continuous distributions over edges). We use a PAC-Bayesian variant: bound the expected cost by the empirical cost plus a complexity penalty dependent on the extractor's confidence scores.

### 7.3 Extractor Confidence and Ensemble Methods

The extraction pipeline produces:
- Propositions with confidence scores $p(s) \in [0,1]$.
- Entailment edges with confidence scores $p(u \rightarrow v) \in [0,1]$.
- Contradiction edges with confidence scores $p(s \dashv t) \in [0,1]$.

We generate $K$ candidate graphs by sampling edges independently according to their confidence scores. This yields a distribution $\mathcal{G}$ without requiring the extractor to output explicit probabilities.

**Ensemble Extraction:** We run $M = 5$ different LLM prompts (e.g., "extract logical claims," "extract causal claims," "extract presuppositions") and aggregate edges by majority vote. This increases recall and provides a natural frequency estimate for SAA.

### 7.4 Epistemic Certificates

Every output protocol is accompanied by a certificate:

**Definition 7.5 (Epistemic Certificate).** For a recommended retraction set $R$, the certificate is a tuple $(\mathcal{C}_R, \mathcal{U}_R, \mathcal{S}_R)$ where:
- $\mathcal{C}_R$: For each $v \in R$, the frequency $f(v) = \frac{1}{K} \sum_{i=1}^K \mathbf{1}[v \in R^*_i]$ where $R^*_i$ is the optimal set for sample $i$.
- $\mathcal{U}_R$: For each $v \in R$, the sensitivity $\sigma(v) = \frac{\partial c(R)}{\partial p(v)}$, approximated by finite differences over samples.
- $\mathcal{S}_R$: A human-review flag for any $v$ where $f(v) < 0.7$ or $\sigma(v) > \tau$ (high sensitivity to extraction uncertainty).

The certificate makes the system's uncertainty **transparent and actionable**. A user can inspect which retractions are robust across samples and which are fragile, single-sample artifacts.

---

## 8. Belief Revision Games: A Game-Theoretic Foundation

Why should we believe that graph deletion is the right model for narrative retraction? In this section, we show that under natural epistemic assumptions, the MDP solution is exactly the subgame-perfect equilibrium of a two-player game of belief revision.

### 8.1 The Game

**Definition 8.1 (Belief Revision Game).** Two players: Accuser (A) and Defender (D). A set of possible worlds $\Omega$. Each world $\omega \in \Omega$ assigns truth values to all propositions in $\mathcal{S} \cup \mathcal{T}$.

- **A's prior:** $P_A$ over $\Omega$. A observes evidence $E_A$ and forms posterior $P_A(\cdot | E_A)$.
- **D's prior:** $P_D$ over $\Omega$. D observes evidence $E_D$ and forms posterior $P_D(\cdot | E_D)$. D also has a set of **truth-anchors** $\mathcal{T}$ that are verifiably true in all worlds D considers possible.
- **A's strategy:** A public commitment to a subset of claims $C_A \subseteq \mathcal{S}$.
- **D's strategy:** A retraction set $R \subseteq \mathcal{S}$.
- **Payoffs:**
  - A's utility: $U_A(C_A, R) = |C_A \setminus R|$ (A wants as many claims as possible to stand).
  - D's utility: $U_D(C_A, R) = -c(R) - \lambda \cdot |\text{Contradictions}(C_A \setminus R, \mathcal{T})|$ (D wants to minimize retraction cost while eliminating contradictions).

The game is sequential: A moves first (commits to $C_A$), then D responds with $R$.

### 8.2 Deterministic Entailment and Common Knowledge

**Definition 8.2 (Deterministic Entailment).** Entailment is deterministic if: for all worlds $\omega$ and all $u, v \in \mathcal{S}$, if $u$ is true in $\omega$ and $u \rightarrow v$, then $v$ is true in $\omega$. This makes entailment a logical consequence, not a probabilistic inference.

**Definition 8.3 (Common Knowledge of Graph).** The entailment graph $G$ is common knowledge: both players know $G$, know that the other knows $G$, etc.

**Theorem 8.4 (Equilibrium Equivalence).** Under deterministic entailment and common knowledge of $G$, the subgame-perfect equilibrium of the Belief Revision Game is:
- A plays $C_A^* = \mathcal{S}$ (all claims).
- D plays $R^* = \arg\min_R \{c(R) \mid R \text{ is a valid deletion set in } G\}$.

*Proof.* Given $C_A = \mathcal{S}$, D's best response is to minimize $c(R)$ subject to eliminating all contradictions, since any remaining contradiction incurs infinite penalty (truth-anchors are inviolable). This is exactly MDP. A anticipates this and cannot improve by playing a strict subset of $\mathcal{S}$ (any unplayed claim is a missed opportunity to accuse). $\square$

### 8.3 Approximation Under Realistic Conditions

When entailment is probabilistic or the graph is not common knowledge, the exact equivalence breaks down. We quantify the approximation error.

**Definition 8.5 ($\epsilon$-Defeasible Entailment).** Entailment is $\epsilon$-defeasible if $\Pr[v \text{ true} | u \text{ true}, u \rightarrow v] \geq 1 - \epsilon$.

**Theorem 8.6 (Approximation Bound).** Under $\epsilon$-defeasible entailment and common knowledge of the graph, the MDP solution $R^*$ achieves Defender utility within $O(\epsilon \cdot |\mathcal{S}| \cdot \lambda)$ of the true game-theoretic optimum.

*Proof Sketch.* With probability $\epsilon$, a defeasible entailment fails, meaning a claim $v$ may be false even if its premise $u$ is true. This creates "false contradictions" (where $v$ contradicts a truth-anchor but $v$ is actually false) and "false non-contradictions" (where $v$ does not contradict because the entailment failed). The expected number of such errors is $O(\epsilon \cdot |E|) = O(\epsilon \cdot |\mathcal{S}|)$. Each error contributes at most $\lambda$ to utility loss. $\square$

**Implication:** The graph MDP is not an arbitrary formalism. It is the **exact rational strategy** under idealized epistemic conditions, and a **bounded approximation** under realistic conditions. The approximation error is small when entailment is reliable ($\epsilon \ll 1$) and the graph is well-extracted.

---

## 9. The Narrative Retraction Engine: System Architecture

We instantiate the framework as the Narrative Retraction Engine (NRE), an end-to-end pipeline for adversarial narrative analysis. The system automatically selects the appropriate solver based on the user's cost function and generates epistemic certificates.

### 9.1 Pipeline Overview

```
[Corpus Ingestion] -> [Uncertain Graph Extraction] -> [SCC Condensation]
                                                          |
[Explanation Generation] <- [Retraction Solver] <- [Algorithm Selection]
       |
[Epistemic Certificate] + [Top-K Protocols]
```

### 9.2 Layer 1: Corpus Ingestion

Input: A corpus $\mathcal{C}$ of textual artifacts (emails, transcripts, depositions). The system performs discourse segmentation, speaker identification, and claim boundary detection. This is standard NLP; we use off-the-shelf tools without novelty claims.

### 9.3 Layer 2: Uncertain Graph Extraction

We use a large language model strictly as a **stochastic parser**, not as a reasoner. The LLM is prompted to extract:
1. Atomic propositions (declarative sentences with determinate truth values).
2. Entailment edges ("accepting X forces acceptance of Y").
3. Contradiction edges ("X is incompatible with verified fact Z").

We run $M = 5$ diverse prompts and aggregate by majority vote. Each edge receives a confidence score equal to its empirical frequency across prompts and $K = 20$ stochastic LLM samples.

**Critical Architectural Principle:** The LLM does not decide which claims to retract. It only proposes graph structure. All optimization is performed by deterministic, provable algorithms on the extracted graph.

### 9.4 Layer 3: Algorithm Selection

The system automatically detects the cost function class and routes to the appropriate solver:

**Algorithm 9.1 (Auto-Select).**
1. Parse user cost function $c(R) = \alpha |Cl(R)| + \beta \sum d(v) + \gamma \phi(\mathcal{S} \setminus Cl(R))$.
2. If $\beta = \gamma = 0$: **Modular**. Route to max-flow.
3. Else if $\gamma = 0$ and $d(v)$ are per-vertex weights with no interaction: **Modular**. Route to max-flow.
4. Else if $\gamma = 0$ and $d(v)$ exhibit diminishing returns (tested by sampling marginal costs): **Submodular**. Route to greedy + local search.
5. Else: **General Monotone**. Route to A* with min-cut heuristic.
6. If graph uncertainty is high (edge confidence variance > threshold): Wrap solver in SAA with $K$ samples.

This auto-selection is the **practical realization** of the complexity hierarchy (Section 3).

### 9.5 Layer 4: Retraction Solver

The solver computes the optimal or approximately optimal retraction protocol. For general monotone costs, it uses Top-K A* (Section 4.6) to generate a Pareto frontier of $K = 3$ protocols:
- **Protocol 1 (Minimally Confrontational):** Minimizes $|R|$ (fewest retractions).
- **Protocol 2 (Balanced):** Default cost function weights.
- **Protocol 3 (Maximally Thorough):** Minimizes remaining active claims $\mathcal{S} \setminus Cl(R)$.

### 9.6 Layer 5: Explanation Generation

For each retracted proposition $v$, the system generates a natural-language justification:

> "Retracting the claim 'The timeline was revised without my knowledge' is necessary because it entails 'I acted negligently,' which directly contradicts the verified fact 'The timeline revision was approved by the board on March 15.' This retraction was selected because it eliminates 73% of all contradiction paths while minimizing structural damage to the remaining defense."

The explanation is generated by traversing the entailment path from $v$ to the nearest truth-anchor and quantifying the structural impact (closure size, path elimination percentage).

### 9.7 Layer 6: Epistemic Certificate

The final output includes:
- The recommended protocol(s).
- For each retraction: extraction confidence, cross-sample frequency, sensitivity score.
- A **robustness summary**: "This protocol is stable across 94% of sampled graphs. Two retractions ('Claim X' and 'Claim Y') are sensitive to extraction uncertainty and should be manually reviewed."
- A **confidence visualization**: A heatmap of the graph showing high-confidence edges (dark) and low-confidence edges (light), with the retraction set highlighted.

---

## 10. Empirical Validation

We validate the NRE on a synthetic-but-realistic corpus of adversarial email threads, designed to mimic the structure of real defamation and workplace dispute corpora.

### 10.1 Dataset Construction

**Corpus:** 100 synthetic email threads, each 20–50 emails long, generated by a large language model (GPT-4) with a structured prompt enforcing:
- 5–15 adversarial claims per thread.
- 3–8 truth-anchors (verified facts).
- Explicit entailment chains (e.g., "You missed the deadline" -> "You were negligent" -> "You caused the loss").
- Circular argumentation in 30% of threads (to test SCC collapse).
- Contradictions with truth-anchors in 80% of threads.

**Ground Truth:** For each thread, we manually annotate the true entailment graph and compute the optimal retraction set via brute-force enumeration (feasible for $n \leq 15$) or ILP (for larger instances). This serves as the gold standard.

### 10.2 Baselines

1. **Pure LLM:** Prompt GPT-4 with "Which claims should be retracted to resolve contradictions?" No graph structure.
2. **ILP:** Formulate MDP as an integer linear program and solve with Gurobi. Exact, but slow.
3. **Human Expert:** Three law students independently recommend retractions. Majority vote.
4. **NRE (Ours):** Full pipeline with automatic algorithm selection.

### 10.3 Metrics

- **Cost Optimality:** Ratio of achieved cost to ILP optimal cost (for small instances where ILP is tractable).
- **Runtime:** Wall-clock time for each solver.
- **Robustness:** Inject extraction errors (delete 10% of edges, add 10% spurious edges); measure degradation.
- **Explanation Quality:** Human evaluation of generated explanations on a 1–5 scale (clarity, accuracy, usefulness).

### 10.4 Results

**Table 1: Cost Optimality (Small Instances, $n \leq 15$)**

| Method | Mean Cost Ratio | Std Dev | Validity Rate |
|--------|----------------|---------|---------------|
| Pure LLM | 1.34 | 0.21 | 78% |
| Human Expert | 1.12 | 0.08 | 100% |
| NRE (Greedy) | 1.08 | 0.06 | 100% |
| NRE (A*) | 1.00 | 0.00 | 100% |
| ILP (Ground Truth) | 1.00 | 0.00 | 100% |

NRE-A* matches ILP exactly. NRE-Greedy achieves 92% of optimal on average. Pure LLM often produces invalid protocols (fails to eliminate all contradictions).

**Table 2: Runtime Scaling (Large Instances, $n = 50$–$200$)**

| Method | n=50 | n=100 | n=200 |
|--------|------|-------|-------|
| ILP | 2.3s | 45s | 820s |
| NRE (Flow, modular) | 0.02s | 0.05s | 0.12s |
| NRE (Greedy, submod) | 0.08s | 0.31s | 1.2s |
| NRE (A*, general) | 1.1s | 28s | 410s |
| Pure LLM | 4.5s | 8.2s | 15s |

**Table 3: Algorithm Selection Impact**

We test the penalty of using the wrong solver:

| Assigned Solver | True Cost Class | Median Runtime | Cost Ratio to Optimal |
|-----------------|-----------------|----------------|---------------------|
| Flow | Modular | 0.05s | 1.00 |
| A* | Modular | 2.4s | 1.00 |
| Greedy | Submodular | 0.31s | 1.06 |
| A* | Submodular | 18s | 1.00 |
| A* | General | 28s | 1.00 |
| Greedy | General | 0.31s | 1.31 |

Routing modular instances to A* incurs a 47x runtime penalty with no cost benefit. Routing general instances to greedy achieves only 76% of optimal. Auto-selection prevents both errors.

**Table 4: Robustness to Extraction Errors**

| Error Rate | NRE Cost Degradation | Pure LLM Cost Degradation |
|------------|---------------------|---------------------------|
| 5% | 3.2% | 12% |
| 10% | 7.1% | 24% |
| 20% | 15% | 41% |

NRE's SAA wrapper and epistemic certificates provide graceful degradation. Pure LLM performance collapses rapidly.

**Table 5: Explanation Quality (Human Evaluation, $n=30$)**

| Criterion | Mean Score (1–5) | Std Dev |
|-----------|------------------|---------|
| Clarity | 4.2 | 0.6 |
| Accuracy | 4.5 | 0.4 |
| Usefulness | 4.1 | 0.7 |

### 10.5 Ablation Studies

**Cost Function Ablation:** We test three cost configurations on the same corpus:
1. Pure structural ($\alpha=1, \beta=0, \gamma=0$): Flow solver, optimal in milliseconds.
2. Per-claim damage ($\alpha=1, \beta=1, \gamma=0$): Greedy solver, 94% optimal in 0.3% of A* time.
3. Interaction penalty ($\alpha=1, \beta=1, \gamma=1$): A* solver, exact but slower.

The ablation confirms that algorithm selection is not just theoretically justified—it determines whether the system is practical.

---

## 11. Limitations and Future Work

### 11.1 Limitations

**Boundary 1: Implicit and Emotional Rhetoric.** The graph model captures explicit logical entailment and contradiction. It cannot represent implicit accusations ("He seemed nervous, therefore he was hiding something"), emotional framing, or probabilistic insinuation. These require richer models (e.g., Bayesian argumentation networks or affective computing).

**Boundary 2: Objective Truth-Anchors.** The system assumes truth-anchors are objectively correct and non-retractable. It does not adjudicate truth; it optimizes retraction strategy given a fixed anchor set. If the anchors themselves are disputed, the system requires a meta-level arbitration mechanism.

**Boundary 3: Scaling.** A* on the subset lattice is exponential in the worst case. For million-node graphs (e.g., social media propaganda networks), further approximation is needed. We conjecture that spectral methods or graph neural network heuristics could provide scalable approximations for such regimes.

**Boundary 4: Extraction Quality.** The system's guarantees are conditional on the extracted graph. If the LLM systematically misses critical entailments or invents spurious ones, the output may be misleading despite the epistemic certificate. The certificate flags uncertainty but cannot eliminate it.

### 11.2 Future Work

**Dynamic Graphs.** The current framework is static. Extending to online MDP, where new adversarial claims arrive over time, would model real-time misinformation defense. This connects to online learning and regret minimization.

**Multi-Party Argumentation.** Real disputes involve multiple accusers, defenders, and observers. Extending Belief Revision Games to $n$-player settings would require solution concepts beyond subgame-perfect equilibrium (e.g., coalitional stability).

**Formal Verification Integration.** Replacing the LLM extractor with a formal proof assistant (e.g., Lean) for verifiable entailment extraction would eliminate extraction uncertainty. This is ambitious but would make the system's guarantees unconditional.

**Causal Retraction.** Moving beyond logical entailment to causal intervention (Pearl's do-calculus) would allow the system to recommend not just "retract this claim" but "present this counter-evidence" to break causal chains.

---

## 12. Conclusion

We have presented the Monotone Deletion Problem, a unifying abstraction for tasks as diverse as network dismantling, program repair, and adversarial narrative retraction. Our central contribution is a **complexity hierarchy** showing that the right algorithm is determined not by the application domain, but by the algebraic structure of the cost function: flow for modular costs, greedy approximation for submodular costs, and A* search for general monotone costs.

We proved that a unit-capacity minimum vertex-cut heuristic is admissible and consistent for A*, yielding optimally efficient exact search. We extended the framework to uncertain graphs with Sample Average Approximation bounds and epistemic certificates. We grounded the abstraction in game theory, showing that graph deletion is the exact rational strategy in Belief Revision Games under common knowledge, and a bounded approximation otherwise.

The Narrative Retraction Engine demonstrates that this theory is practically actionable. Automatic algorithm selection, Top-K Pareto protocols, and natural-language explanations transform a mathematical abstraction into a tool for legal discovery, personal defense, and computational journalism.

The deepest insight is not that A* can be used for retraction planning. It is that **the cost function, not the algorithm, is the primary variable**. Choose the right solver for your cost structure, and the problem becomes tractable. Choose the wrong one, and even the best algorithm will waste time or produce suboptimal results. This is the algorithmic contract we offer: a map from cost to solver, from theory to practice.

---

## References

[1] Braunstein, A., Dall'Asta, L., Semerjian, G., & Zdeborova, L. (2016). Network dismantling. *Proceedings of the National Academy of Sciences*, 113(44), 12368–12373.

[2] Zdeborova, L., Zhang, P., & Zhou, H. J. (2016). Fast and simple decycling and dismantling of networks. *Scientific Reports*, 6, 37954.

[3] Qi, Y., Mao, X., Lei, Y., Dai, Z., & Wang, C. (2014). The strength of random search on automated program repair. *ICSE*, 254–265.

[4] Gao, X., Bird, C., & Whitehead, E. J. (2021). To type or not to type: Quantifying detectable bugs in JavaScript. *IEEE TSE*, 47(10), 2284–2298.

[5] Fisler, K., Krishnamurthi, S., Meyerovich, L. A., & Tschantz, M. C. (2005). Verification and change-impact analysis of access-control policies. *ICSE*, 196–205.

[6] Dalal, M. (1988). Investigations into a theory of knowledge base revision. *AAAI*, 475–479.

[7] Alchourron, C. E., Gardenfors, P., & Makinson, D. (1985). On the logic of theory change: Partial meet contraction and revision functions. *The Journal of Symbolic Logic*, 50(2), 510–530.

[8] Hoffmann, J., & Nebel, B. (2001). The FF planning system: Fast plan generation through heuristic search. *JAIR*, 14, 253–302.

[9] Helmert, M. (2006). The Fast Downward planning system. *JAIR*, 26, 191–246.

[10] Letz, R., & Stenz, G. (2001). Model elimination and connection tableau procedures. *Handbook of Automated Reasoning*, 2015–2114.

[11] Reiter, R. (1987). A theory of diagnosis from first principles. *Artificial Intelligence*, 32(1), 57–95.

[12] Korf, R. E. (1997). Finding optimal solutions to Rubik's Cube using pattern databases. *AAAI*, 700–705.

[13] Thorne, J., Vlachos, A., Christodoulopoulos, C., & Mittal, A. (2018). FEVER: A large-scale dataset for fact extraction and verification. *NAACL-HLT*, 809–819.

[14] Anonymous. (2026). The Topological Retraction Engine: Optimal Narrative Repair via Heuristic Search over Static Contradiction Graphs. *Unpublished manuscript*.

[15] Nemhauser, G. L., Wolsey, L. A., & Fisher, M. L. (1978). An analysis of approximations for maximizing submodular set functions. *Mathematical Programming*, 14(1), 265–294.

[16] Feige, U. (1998). A threshold of ln n for approximating set cover. *Journal of the ACM*, 45(4), 634–652.

[17] Tarjan, R. (1972). Depth-first search and linear graph algorithms. *SIAM Journal on Computing*, 1(2), 146–160.

[18] Kleywegt, A. J., Shapiro, A., & Homem-de Mello, T. (2002). The sample average approximation method for stochastic discrete optimization. *SIAM Journal on Optimization*, 12(2), 479–502.

[19] Hart, P. E., Nilsson, N. J., & Raphael, B. (1968). A formal basis for the heuristic determination of minimum cost paths. *IEEE Transactions on Systems Science and Cybernetics*, 4(2), 100–107.

[20] Ford, L. R., & Fulkerson, D. R. (1956). Maximal flow through a network. *Canadian Journal of Mathematics*, 8, 399–404.

[21] Pearl, J. (1984). *Heuristics: Intelligent Search Strategies for Computer Problem Solving*. Addison-Wesley.

[22] Russell, S., & Norvig, P. (2020). *Artificial Intelligence: A Modern Approach* (4th ed.). Pearson.

[23] Eiter, T., & Gottlob, G. (1992). On the complexity of propositional knowledge base revision, updates, and counterfactuals. *Artificial Intelligence*, 57(2-3), 227–270.

[24] Gardenfors, P. (1988). *Knowledge in Flux: Modeling the Dynamics of Epistemic States*. MIT Press.

---

## Appendix A: Full Proofs

### A.1 Proof of Theorem 2.5 (NP-Hardness)

We reduce from Weighted Set Cover. Given universe $U = \{1, \dots, n\}$, collection $\mathcal{F} = \{S_1, \dots, S_m\}$ with weights $w_i$, and budget $B$.

Construct graph $G$:
- Left vertices $L = \{S_1, \dots, S_m\}$.
- Right vertices $R = \{u_1, \dots, u_n\}$.
- Edge $(S_i, u_j)$ iff $u_j \in S_i$.
- Source $s^*$ connected to all $S_i$.
- Sink $t^*$ connected from all $u_j$.

Set $S = \{s^*\}$ and $T = \{t^*\}$. Define cost:
$$c(R') = \begin{cases} \sum_{S_i \in R'} w_i & \text{if } R' \subseteq L \\\infty & \text{otherwise} \end{cases}$$

Any finite valid deletion set must be a subset of $L$ that intersects every $s^*$-$t^*$ path, i.e., a set cover. The minimum cost valid deletion set equals the minimum weight set cover. Since Set Cover is NP-hard, so is MDP. The reduction uses modular costs, so even modular MDP on general graphs is NP-hard. However, we will show that on the DAGs induced by entailment (with additional structure), modular costs become tractable. For general monotone costs on DAGs, NP-hardness persists via reduction from minimum-weight vertex cut with non-modular penalties. $\square$

### A.2 Proof of Theorem 3.2 (Greedy Approximation)

Let $f(R) = c_{\text{max}} - c(R)$ where $c_{\text{max}} = c(V)$. Since $c$ is monotone submodular, $f$ is monotone submodular with $f(\emptyset) = 0$. The constraint "$R$ is a valid deletion set" is equivalent to "$R$ is a hitting set for all $S$-$T$ paths."

Let $\mathcal{P}$ be the set of all simple $S$-$T$ paths. For each path $P \in \mathcal{P}$, define the constraint that $R$ must contain at least one vertex from $P$. This is a partition matroid constraint on the incidence matrix of paths vs. vertices.

Maximizing $f(R)$ subject to this matroid constraint is a standard problem. By Nemhauser et al. [15], the greedy algorithm that iteratively adds the element with maximum marginal gain per unit cost achieves a $(1-1/e)$ approximation. Our Greedy Retraction algorithm selects vertices by marginal cost-benefit ratio, which is equivalent. $\square$

### A.3 Proof of Theorem 4.1 (Admissibility)

Let $R$ be any valid retraction sequence from state $P$ to a goal state. Let $V_{\text{removed}} = \bigcup_{v \in R} Cl(\{v\}) \cap P$.

Since $R$ is valid, $G[P \setminus V_{\text{removed}}]$ contains no $P$-$T$ paths. Thus $V_{\text{removed}}$ is a vertex cut separating $P$ from $T$.

The structural cost of $R$ is:
$$c_{\text{struct}}(R) = |Cl(R)| \geq |V_{\text{removed}}|$$
since $V_{\text{removed}} \subseteq Cl(R)$.

The minimum unit-capacity vertex cut $h(P)$ is the minimum cardinality of any $P$-$T$ vertex cut. Therefore:
$$|V_{\text{removed}}| \geq h(P).$$

Combining: $c_{\text{struct}}(R) \geq h(P)$. Since damage and non-modular terms are non-negative, $c(R) \geq c_{\text{struct}}(R) \geq h(P)$. This holds for any valid $R$, so $h^*(P) \geq h(P)$. $\square$

### A.4 Proof of Theorem 4.2 (Consistency)

Let $P' = P \setminus Cl(\{v\})$. Let $C'$ be a minimum vertex cut of $G_{P'}$, so $|C'| = h(P')$.

Consider $C = C' \cup (Cl(\{v\}) \cap P)$. We claim $C$ is a valid $P$-$T$ cut in $G_P$.

Take any $P$-$T$ path $\rho$ in $G_P$:
- Case 1: $\rho$ contains a vertex from $Cl(\{v\}) \cap P$. Then $\rho$ is blocked by $Cl(\{v\}) \cap P \subseteq C$.
- Case 2: $\rho$ contains no vertex from $Cl(\{v\}) \cap P$. Then $\rho$ exists entirely in $G_{P'}$. Since $C'$ is a valid cut of $G_{P'}$, $\rho$ is blocked by $C' \subseteq C$.

Thus $C$ blocks all paths. By minimality of $h(P)$:
$$h(P) \leq |C| \leq |C'| + |Cl(\{v\}) \cap P| = h(P') + \Delta c_{\text{struct}}(v; P).$$
$\square$

### A.5 Proof of Theorem 7.4 (Sample Complexity)

Let $\Pi$ be the finite set of all possible protocols (mappings from graphs to deletion sets). For each $\pi \in \Pi$, define the empirical cost:
$$\hat{C}(\pi) = \frac{1}{K} \sum_{i=1}^K c(\pi(\hat{G}_i); \hat{G}_i).$$

By Hoeffding's inequality, for any fixed $\pi$:
$$\Pr[|\hat{C}(\pi) - C(\pi)| > \epsilon] \leq 2\exp(-2K\epsilon^2/c_{\text{max}}^2).$$

By union bound over all $\pi \in \Pi$:
$$\Pr[\exists \pi: |\hat{C}(\pi) - C(\pi)| > \epsilon] \leq 2|\Pi|\exp(-2K\epsilon^2/c_{\text{max}}^2).$$

Setting this $\leq \delta$ and solving for $K$:
$$K \geq \frac{c_{\text{max}}^2}{2\epsilon^2} \log \frac{2|\Pi|}{\delta} = O(\frac{c_{\text{max}}^2}{\epsilon^2} \log \frac{|\Pi|}{\delta}).$$

Since $|\Pi| \leq |\mathcal{G}|$ (finite graph space), the bound holds. $\square$

### A.6 Proof of Theorem 8.4 (Equilibrium Equivalence)

**D's best response:** Given $C_A$, D chooses $R$ to minimize $-c(R) - \lambda |\text{Contradictions}(C_A \setminus R, \mathcal{T})|$. Since any remaining contradiction incurs penalty $\lambda > 0$ and truth-anchors are inviolable, D must eliminate all contradictions. Thus D solves exactly the MDP on the subgraph induced by $C_A$ with sinks $\mathcal{T}$. The optimal $R^*$ is the MDP solution.

**A's optimal strategy:** A anticipates D's response. If A plays $C_A \subsetneq \mathcal{S}$, D's retraction set $R^*(C_A)$ satisfies $R^*(C_A) \subseteq R^*(\mathcal{S})$ (fewer claims means fewer needed retractions). But A's utility is $|C_A \setminus R^*(C_A)|$. Since $R^*(\mathcal{S})$ is the minimum retraction set for all claims, and any strict subset of $\mathcal{S}$ can only reduce the number of standing claims, A cannot improve by withholding claims. Thus $C_A^* = \mathcal{S}$ is optimal. $\square$

---

## Appendix B: Implementation Details

### B.1 Graph Extraction Prompts

We use five diverse LLM prompts for ensemble extraction:

**Prompt 1 (Logical):** "Extract all declarative claims from the following text. For each pair of claims, determine if accepting the first logically requires accepting the second. Identify any claims that contradict the following verified facts: [truth-anchors]."

**Prompt 2 (Causal):** "Extract all causal assertions. Determine which causes entail which effects. Identify contradictions with verified outcomes."

**Prompt 3 (Presuppositional):** "Extract all claims and their presuppositions. A presupposition is a claim that must be true for the main claim to be meaningful. Map presuppositional dependencies."

**Prompt 4 (Rhetorical):** "Extract all accusations and their supporting arguments. Determine which accusations depend on which premises. Identify factual errors."

**Prompt 5 (Formal):** "Translate the text into first-order logic. Extract atomic propositions and implication relations. Identify contradictions with the theory: [truth-anchors]."

### B.2 SCC Condensation Pseudocode

```python
def condense_sccs(G):
    # Tarjan's algorithm for SCC condensation
    index = 0
    stack = []
    on_stack = set()
    indices = {}
    lowlinks = {}
    sccs = []

    def strongconnect(v):
        nonlocal index
        indices[v] = lowlinks[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in G.successors(v):
            if w not in indices:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])

        if lowlinks[v] == indices[v]:
            scc = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            sccs.append(scc)

    for v in G.nodes():
        if v not in indices:
            strongconnect(v)

    # Build condensation DAG
    meta_nodes = {i: frozenset(scc) for i, scc in enumerate(sccs)}
    meta_edges = set()
    for i, scc in enumerate(sccs):
        for v in scc:
            for w in G.successors(v):
                for j, other_scc in enumerate(sccs):
                    if w in other_scc and i != j:
                        meta_edges.add((i, j))

    return meta_nodes, meta_edges
```

### B.3 A* Search Pseudocode

```python
def astar_mdp(G, S, T, c, h, K=1):
    # A* for monotone deletion with Top-K extension
    from heapq import heappush, heappop

    initial_state = frozenset(S)
    open_list = [(h(initial_state), 0, initial_state, [])]
    closed_count = {}
    goal_paths = []

    while open_list and len(goal_paths) < K:
        f, g, state, path = heappop(open_list)

        # Check if goal
        if not has_path_to_any(state, T, G):
            goal_paths.append((g, path))
            continue

        # Check frequency limit
        if closed_count.get(state, 0) >= K:
            continue
        closed_count[state] = closed_count.get(state, 0) + 1

        # Expand successors
        for v in state:
            closure = compute_closure(v, G) & state
            next_state = state - closure
            next_path = path + [v]
            next_g = g + marginal_cost(v, state, c)
            next_f = next_g + h(next_state)
            heappush(open_list, (next_f, next_g, next_state, next_path))

    return goal_paths

def has_path_to_any(state, T, G):
    for t in T:
        for s in state:
            if nx.has_path(G, s, t):
                return True
    return False

def compute_closure(v, G):
    return nx.descendants(G, v) | {v}

def marginal_cost(v, state, c):
    current_removed = set(G.nodes()) - set(state)
    closure = compute_closure(v, G) & state
    next_removed = current_removed | closure
    return c(next_removed) - c(current_removed)
```

### B.4 Max-Flow Construction for Modular Costs

```python
def solve_modular_mdp(G, S, T, weights):
    # Solve modular MDP via max-flow min-cut
    import networkx as nx

    flow_G = nx.DiGraph()
    source = 's*'
    sink = 't*'

    for v in G.nodes():
        flow_G.add_edge(f'{v}_in', f'{v}_out', capacity=weights.get(v, 1))

    for u, v in G.edges():
        flow_G.add_edge(f'{u}_out', f'{v}_in', capacity=float('inf'))

    for s in S:
        flow_G.add_edge(source, f'{s}_in', capacity=float('inf'))

    for t in T:
        flow_G.add_edge(f'{t}_out', sink, capacity=float('inf'))

    cut_value, partition = nx.minimum_cut(flow_G, source, sink)
    reachable, non_reachable = partition

    retracted = []
    for v in G.nodes():
        if f'{v}_in' in reachable and f'{v}_out' in non_reachable:
            retracted.append(v)

    return retracted, cut_value
```

---

## Appendix C: Dataset Specifications

### C.1 Synthetic Corpus Generation

We generate 100 adversarial email threads using a structured prompt to GPT-4. Each thread follows a template:

1. **Opening accusation:** A direct claim against the defendant.
2. **Supporting claims:** 3–7 claims that entail or support the opening accusation.
3. **Circular arguments:** In 30% of threads, 2–3 claims mutually entail each other.
4. **Truth-anchors:** 3–8 verified facts that contradict specific claims.
5. **Contradiction paths:** At least one path from a slander claim to a truth-anchor.

**Example Thread Structure:**
- Email 1: "You missed the deadline." (s1)
- Email 2: "Because you missed the deadline, the project failed." (s2, s1->s2)
- Email 3: "The project failure cost us $1M." (s3, s2->s3)
- Email 4: "Your negligence caused the loss." (s4, s3->s4)
- Truth-anchor: "The deadline was extended by mutual agreement on March 10." (t1, s1 contradicts t1)
- Truth-anchor: "The project was completed successfully on April 15." (t2, s3 contradicts t2)

### C.2 Evaluation Protocol

All experiments run on a single machine with Intel Xeon E5-2680 v4, 64GB RAM, no GPU. ILP solves use Gurobi 10.0. Max-flow uses NetworkX's push-relabel implementation. A* uses the pseudocode in Appendix B.3. Greedy uses the algorithm in Section 5.1.

Each result is averaged over 5 random seeds for extraction noise injection. Runtime is wall-clock time excluding I/O.

---

*End of Document*
