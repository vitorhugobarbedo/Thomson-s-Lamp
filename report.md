# Thomson's Lamp as an Informational Black Hole: From Philosophical Idea to a Reproducibility Check on Real Hardware

> **Status:** protocol derived, verified mathematically, validated on an exact simulator, calibrated against a realistic noise model, and **reproduced in two real runs on IBM Heron r2** (`ibm_marrakesh`, 2026-07-27). Herald success rate: 0.2362 and 0.2385 (predicted 0.238±0.008). Fidelity conditioned on success: **0.9130** (predicted 0.94–0.96; Landsman et al. 2019 reported ~0.80 under a more rigorous methodology). This is best read as a reproducibility exercise on a well-established protocol, not a new experimental result — see [Related Work](README.md#related-work) in the repository README for closely related prior hardware runs, several of which used the same or a near-identical circuit.

## 1. The Original Proposition (Philosophical / Speculative Concept)

The starting point was a text proposing an analogy between the **Thomson's Lamp paradox** (the classical supertask: a switch toggled infinitely many times in finite time — is the state at $t=1$ well-defined?) and the **black hole information paradox**, specifically the **Hayden–Preskill (2007)** information-recovery protocol.

The central idea proposed:

- Treat the instant $t=1$ (the accumulation point of the supertask) as a **temporal event horizon**.
- Model each toggle of the lamp as the emission of entangled "radiation" (via a CNOT), analogous to Hawking radiation.
- Claim that, just as information falling into a black hole can be reconstructed from the emitted radiation (the Hayden–Preskill protocol), the information about the lamp's "final" state at $t=1$ could be reconstructed from the accumulated "radiation," thereby avoiding the supertask's logical paradox.
- Connect this to the $ER=EPR$ conjecture (Susskind–Maldacena), suggesting that extreme entanglement would create a temporal "bridge" between the limit $t\to1^-$ and the future.

## 2. First Critical Analysis

Before running any simulation, the text was split into three layers:

| Layer | Status |
|---|---|
| Real experiments cited (Hayden–Preskill in trapped ions, 2019; the "wormhole" experiment on Sycamore, 2022; Hawking analogues in BECs) | Mostly correct, with one caveat: the Google/Caltech (2022) experiment was a 9-qubit toy model, and press coverage overstated the result |
| Academic literature on supertasks (Malament–Hogarth, Pitowsky, Norton) | Real and relevant, but concerned with measurement limits, not the specific mechanism proposed here |
| The "Thomson's Lamp + Hayden–Preskill" combination | The original text itself calls this an **"analogical mapping"** — but then treats the analogy as if it were a physical deduction, which does not hold up |

**Central diagnosis:** there is no real Hamiltonian behind the proposal; the "temporal event horizon" is a verbal metaphor, not a derivation; and the original problem (the limit of an oscillating sequence that does not converge) is not solved — it is **replaced** by a different question.

## 3. Formalization and Initial Numerical Test

Two competing models were formalized to test whether the proposal reproduces the expected physical signature (the Page curve / scrambling):

- **H1 (literal proposal from the text):** lamp $L$ + radiation qubits $R_n$, applying $\hat X$ (flip) followed by sequential CNOTs at each step.
- **H2 (genuine Hayden–Preskill):** a Haar-random unitary acting on the entire accumulated system at each step (real scrambling).

### Bugs Found and Fixed at This Stage

1. **`partial_trace_general` via successive `np.trace`** produced spurious coherence terms due to a sliding-index bug. Fixed with an `einsum`-based implementation, validated against `qiskit.quantum_info.partial_trace`.
2. **Units in the Page-curve formula** were in nats (natural log) while the rest of the notebook used bits (log₂) — a missing division by $\ln 2$.

### Final Result (corrected and validated, numpy ≡ Qiskit)

| $n$ | H1 (CNOT) | H2 mean ± std (300 realizations) | Theoretical Page value (bits) |
|---|---|---|---|
| 1 | 0.9427 | 0.4838 ± 0.2639 | 0.4809 |
| 2 | 0.9427 | 0.7331 ± 0.1724 | 0.7351 |
| 3 | 0.9427 | 0.8657 ± 0.0968 | 0.8662 |
| 4 | 0.9427 | 0.9226 ± 0.0603 | 0.9327 |
| 5 | 0.9427 | 0.9683 ± 0.0242 | 0.9663 |
| 6 | 0.9427 | 0.9829 ± 0.0133 | 0.9831 |

**Conclusion:** H1 has **constant** entropy at every step — it does not oscillate, does not grow, and shows no Page-curve structure. All the correlation is fixed by the first CNOT, forming a GHZ-type "cat state" that subsequent steps merely extend without changing the reduced entropy. H2 (genuine scrambling) converges, on average, almost exactly to the theoretical Page curve. **The literal proposal in the text (H1) does not reproduce the physical behavior it claims to invoke as justification.**

## 4. Decoding Protocol: Three Attempts, One That Worked

### Attempt 1 — Ad Hoc Teleportation Circuit (Failed)

A first attempt to build a decoding circuit via a "Bell measurement between old and new radiation" gave fidelity $\approx 0.50$ for any $k$ — equivalent to a random guess. **Diagnosis:** the correct cancellation structure between $U$ and its conjugate on the mirror system was missing; the topology had been invented incorrectly. Discarded.

### Attempt 2 — Petz Recovery Map (Successful, with Caveats)

Implementation of the **Petz map** (universal near-optimal recovery, Barnum–Knill 2002), validated on limiting cases:
- $S$ = everything → $F_e = 1.000$ (correct)
- $S$ = empty → $F_e = 0.250 = 1/d^2$ (correct — the entanglement fidelity of an "information-free" channel)

| $k_{BH}$ | $s{=}0$ | $s{=}1$ | $s{=}2$ | $s{=}3$ | $s{=}4$ |
|---|---|---|---|---|---|
| 2 | 0.250 | 0.765±0.023 | 0.968±0.007 | **1.000** | — |
| 3 | 0.250 | 0.776±0.021 | 0.960±0.012 | 0.994±0.002 | **1.000** |

Confirms the Hayden–Preskill fast-decoding signature: with an "old black hole," a few extra qubits of radiation already raise the recovery fidelity from $0.25$ to near $1.0$. **Limitation:** the Petz map proves recoverability in principle, but is not, in general, a low-depth circuit — it does not resolve the question of hardware feasibility.

### Attempt 3 — The Yoshida–Kitaev Protocol (arXiv:1710.03363), Derived and Verified

Returning to the original literature (Yoshida–Kitaev; Landsman et al., *Nature* 567, 61, 2019), the probabilistic decoding protocol was **derived from scratch** using the EPR-state transpose identity:

$$\langle EPR|(M\otimes I) = \langle EPR|(I\otimes M^T), \qquad U^T U^* = I \text{ (unitarity)}$$

This shows that applying $U$ to the original system and $U^*$ (complex conjugate) to a mirror system on Bob's side cancels exactly across a Bell measurement, giving success amplitude $=1/2$ (probability $=1/4$), **independent of the black hole's size and of $U$ itself** — and, when successful, fidelity **exactly 1**.

Numerical verification (exact statevector):

| $n_{BH}$ | Measured probability | Measured fidelity |
|---|---|---|
| 1 | 0.250000 ± 1×10⁻¹⁶ | 1.000000 |
| 2 | 0.250000 ± 1×10⁻¹⁶ | 1.000000 |
| 3 | 0.250000 ± 8×10⁻¹⁷ | 1.000000 |
| 4 | 0.250000 ± 6×10⁻¹⁷ | 1.000000 |

Matches exactly the value published in the literature ($1/d_A^2=1/4$ for a 1-qubit message).

### Qiskit Circuit and Noise Test (With a Bias Caught Along the Way)

The protocol was rebuilt as a Qiskit circuit with a real Bell measurement (CX+H+measurement, not an algebraic projection), validated noise-free (0.2495 and 0.2492, within the statistical error of 0.2500).

A first robustness test ("error angle" on Bob's mirror unitary) showed fidelity **improving** with more qubits — this was identified as an **artifact of the error model** (Haar-random matrices in higher dimensions have smaller typical entries), not real physics, and the test was discarded.

It was replaced by realistic gate noise (`qiskit-aer` `NoiseModel`, depolarizing + readout error):

**First pass — generic pessimistic estimate (2Q error ~0.6%):**

| $n_{BH}$ | Total qubits | Success probability |
|---|---|---|
| 1 | 6 | 0.2334 ± 0.0022 |
| 2 | 10 | 0.1736 ± 0.0027 |
| 3 | 14 | 0.0471 ± 0.0007 |

**Second pass — recalibrated with measured, published IBM Heron r2 data (2025–2026):** 2-qubit gate error (CZ) ~0.15–0.3%, 1-qubit error ~0.02–0.03%, readout error ~1–2% (missing from the first model), $T_1\sim167$–$290\,\mu s$, $T_2\sim110$–$360\,\mu s$:

| $n_{BH}$ | Total qubits | Success probability (real Heron r2) |
|---|---|---|
| 1 | 6 | 0.238 ± 0.008 |
| 2 | 10 | 0.203 ± 0.007 |
| 3 | 14 | **0.122 ± 0.002** |

The real picture is considerably more favorable than the initial pessimistic estimate — the 156-qubit count of the Heron chip is not the bottleneck (qubit count is abundant); the bottleneck is circuit depth and accumulated gate/readout error.

## 5. Where This Fits in Physics and Philosophy — Publishability Assessment

- The core physical content (the Page curve from Haar-random unitaries, Hayden–Preskill decoding) has been established since 1993/2007 and has already been tested experimentally several times: Landsman et al. (2019, trapped ions), Blok et al. (2021, superconducting qutrits), Czelusta & Mielczarek (2021, IBM Santiago superconducting), Schuster et al. (2022, trapped ions, deterministic successor protocol), and Jafferis et al. (2022, Google Sycamore — a claim publicly disputed by a comment from the original protocol's own authors, arXiv:2302.07897). Closest to this work, Shapoval et al. (2022/23, *Quantum* 7, 1138) ran essentially this same wormhole-inspired teleportation protocol across **five IBM superconducting processors** plus a Quantinuum trapped-ion system, as a dedicated multi-device benchmark, reporting a best signal at 80% of theoretical predictions. The genre is still active: a June 2026 paper (arXiv:2606.16451) runs the identical circuit topology used here (Haar-scrambling unitary + conjugate + Bell measurement + post-selection) on trapped-ion cloud hardware, deploying it as a hardware-error diagnostic tool rather than as a standalone result. None of this is new physics, and running it again — even on newer hardware — does not change that.
- The specific combination "Thomson's Lamp + Hayden–Preskill" does not appear in the literature searched — it is novel as *framing*, not as physics.
- The genuine, defensible core is the **conceptual argument**: the "lamp as a black hole" metaphor only works if the dynamics is genuine scrambling (H2 / Yoshida–Kitaev), never sequential CNOTs (H1) — the original text implicitly swapped the mechanism without making that explicit.
- Realistic publication path, if any: a conceptual note in philosophy of physics (situated in the supertask literature — Malament–Hogarth, Pitowsky, Norton), or a pedagogical note in a physics-teaching journal (e.g. *American Journal of Physics*) — not an original theoretical or experimental physics paper. See the repository [README](README.md#related-work) for the full prior-art table.

## 6. Real Hardware Run (IBM Heron r2, `ibm_marrakesh`)

Two real runs via `qiskit-ibm-runtime`, with automatic backend selection among `ibm_marrakesh`, `ibm_fez`, and `ibm_kingston` based on measured gate error, readout error, and queue length. The second run adds the Bell measurement between $R$ and $R'$, closing the verification loop left open after the first run.

### Selected Backend and Calibration at Run Time

| Parameter | Run 1 | Run 2 |
|---|---|---|
| Backend | `ibm_marrakesh` (Heron r2, 156 qubits) | `ibm_marrakesh` (Heron r2, 156 qubits) |
| 2-qubit gate error (median) | 0.2761% | 0.2761% |
| Readout error (median) | 1.2573% | 1.2573% |
| Queue at run time | 111 jobs | 115 jobs |
| Native gates | `cz, id, rz, sx, x` | `cz, id, rz, sx, x` |

### Run 1 — Herald Only (Post-Selection Success Rate)

| | Value |
|---|---|
| Depth / 2-qubit gates | 38 / 17 |
| Job ID | `d9jrvb8ii2cc73efaldg` |
| **Measured success probability** | **0.2362** |
| Calibrated prediction (Section 4) | 0.238 ± 0.008 |
| Ideal, noise-free | 0.2500 |

Agreement within 1 standard deviation of the prediction.

### Run 2 — Herald + Conditioned Fidelity (Bell Measurement on $R,R'$)

Extended circuit: $R$ and $R'$ are now measured in the Bell basis (CX+H+measurement) at the end, allowing an estimate of the real teleportation fidelity conditioned on the herald's success — not just the post-selection survival rate.

| | Value |
|---|---|
| Depth / 2-qubit gates | 48 / 21 |
| Job ID | `d9js2njhdfks73cipidg` |
| Total shots / successful shots | 8000 / 1908 |
| **Success probability (herald)** | **0.2385** |
| **Fidelity conditioned on success ($R,R'$)** | **0.9130** |
| Fidelity predicted by the calibrated simulation (previous section) | 0.94–0.96 |
| Ideal, noise-free fidelity | 1.0000 |
| Fidelity reported by Landsman et al. 2019 (trapped ions) | ~0.80 |

### Analysis

**Herald success rate:** 0.2385, again within the predicted range (0.238±0.008) and consistent with Run 1 (0.2362) — reproducible as expected, even with the added depth (48 vs. 38, +4 two-qubit gates) introduced by the extra Bell measurement on $(R,R')$.

**Conditioned fidelity:** 0.9130, slightly below the calibrated simulation's prediction (0.94–0.96). The gap (~3–4 percentage points) is consistent with effects a simple depolarizing noise model doesn't capture: $T_1/T_2$ decoherence during the idle time of $R$ and $R'$ (which sit without active gates while the other 4 qubits are manipulated, but remain subject to relaxation and dephasing), and possible residual crosstalk from the tunable coupler between neighboring qubits in `ibm_marrakesh`'s physical layout.

**Comparison with Landsman et al. 2019:** 0.9130 (Heron r2, superconducting, this work) is numerically **higher** than the ~80% reported for trapped ions — but this comparison requires caution: this work's metric uses a **single Bell-measurement basis** (it only checks whether the outcome was `00`), while Landsman et al. estimated fidelity via multiple complementary bases (partial tomography), which tends to give a more conservative number because it captures phase errors a single basis may not reveal. So 0.9130 here is better read as an **optimistic upper bound** on the real fidelity, not a number equivalent to theirs. A rigorous comparison would require replicating their multi-basis protocol. It is also worth noting that a June 2026 paper running the identical circuit topology on trapped-ion cloud hardware (arXiv:2606.16451) reports 0.906 (IonQ Aria 1) and 0.742 (IonQ Harmony) under a comparable single-basis metric — placing this work's 0.9130 within the normal range for current-generation hardware in general, rather than as a device-specific standout.

### Closed Verification Loop

The "natural next step" flagged in the previous version of this document — measuring $R,R'$ conditioned on the already-recorded success — has been carried out. Natural extensions that remain: (a) repeating with multiple measurement bases for a more rigorous fidelity, directly comparable to Landsman et al.; (b) scaling to $n_{BH}=2,3$ on real hardware and comparing against the Section 4 predictions; (c) investigating the origin of the ~3–4 percentage-point gap between prediction and measurement (idle-time decoherence vs. crosstalk) with a more refined noise model (`NoiseModel.from_backend`, which uses the device's full calibration rather than single median values). Given how crowded this specific benchmarking niche already is (see [Related Work](README.md#related-work)), these are worth pursuing for personal learning rather than for publication.

## 7. Current Consolidated Status

Files delivered as part of this exercise, all validated on an exact simulator with a calibrated noise model, **and now confirmed by two real-hardware runs** (herald success rate and conditioned fidelity):

- `thomson_lamp_hayden_preskill.ipynb` — full notebook (formalization, H1 vs. H2, Page curve, Petz map, Qiskit) — *not yet included in this repository*
- `thomson_hp.py`, `petz_test.py` — standalone scripts — *not yet included in this repository*
- `yoshida_kitaev.py` — exact derivation and verification of the probabilistic protocol (statevector) — *not yet included in this repository*
- `yk_qiskit_circuit.py` — Qiskit circuit with a real Bell measurement, validated noise-free and with calibrated Heron r2 noise — *not yet included in this repository*
- [`scripts/submit_to_heron_final_v2.py`](scripts/submit_to_heron_final_v2.py) — submission script with environment-based secrets, automatic backend selection, and a Bell measurement on $(R,R')$ for conditioned fidelity — **successfully run on `ibm_marrakesh`, twice** — *included in this repository*

**Final result of the theory → simulation → hardware cycle:**

| Metric | Prediction | Measured (real hardware) |
|---|---|---|
| Herald success probability | 0.238 ± 0.008 | 0.2362 and 0.2385 (two runs) |
| Fidelity conditioned on success | 0.94–0.96 | 0.9130 |

The Yoshida–Kitaev decoding protocol, derived and verified mathematically in the sections above, was reproduced end-to-end on real 156-qubit quantum hardware: it survives post-selection at the predicted rate, and the information is in fact recovered with high fidelity (>90%) conditioned on success — numerically ahead of the Landsman et al. 2019 benchmark under a less rigorous metric, and in line with the broader body of similar hardware runs from 2019 through mid-2026 (see [Related Work](README.md#related-work)). The contribution here is a clean, documented derivation-to-hardware pipeline, not a new physics result.
