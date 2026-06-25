# Uncertainty-quantified risk-value scheduling for vehicle-UAV transmission line inspection

Author names withheld for review

## Highlights

- A vehicle-UAV inspection model couples probabilistic energy prediction with risk-value scheduling.
- A chance-constrained sortie filter converts energy uncertainty into conservative dispatch actions.
- Event-triggered rolling ALNS improves disturbed-operation performance over static and periodic replanning.
- Synthetic experiments follow a reusable TRE-style output protocol with raw data, source figures, and verified references.

## Abstract

Vehicle-UAV collaboration is a promising mode for large-scale transmission-line inspection, yet most scheduling models still rely on deterministic endurance estimates and homogeneous task values. This paper formulates infrastructure inspection as an uncertainty-aware and risk-value aware vehicle-UAV scheduling problem. We propose UQ-RV-ALNS, a framework that combines a probabilistic physics-informed energy surrogate, a chance-constrained sortie feasibility filter, a risk-value objective for high-priority inspection tasks, and event-triggered rolling replanning under wind, road-delay, urgent-task and communication disturbances. In this legacy controlled synthetic simulation suite, UQ-RV-ALNS reduces risk-weighted completion time by 37.5% relative to nearest-stop routing and by 0.5% relative to point-PINN ALNS; the 4.7-percentage-point top-risk coverage change is reported as descriptive simulation evidence. Under high uncertainty, the proposed conservative dispatch layer reduces the mean infeasible-sortie rate from 0.75% to 0.00% with a 0.24% makespan change. In disturbed online episodes, event-triggered replanning reduces makespan by 5.1% relative to a static plan and eliminates the simulated violation rate observed in static operation. The evidence is simulation-based and should be interpreted as algorithmic validation rather than field deployment validation.

Keywords: vehicle-UAV routing; transmission line inspection; adaptive large neighborhood search; physics-informed energy prediction; chance constraints; online replanning

## 1. Introduction

Drone-assisted logistics and inspection research has moved from stylized truck-drone routing toward richer air-ground systems with energy supply, no-fly zones, multimodal integration, automated heuristic design and synchronized truck-drone fulfillment \cite{kim2026bidirectional,liu2026evtol,zhang2026airground,shi2026llm,yang2025integrated}. Transmission-line inspection shares this operational structure but differs from retail delivery in three important respects. First, the value of inspecting a tower or line segment is heterogeneous because defect likelihood, line criticality and image-risk priors vary spatially. Second, feasibility depends on energy and endurance under wind, payload, temperature and battery reserve uncertainty. Third, practical operation is rarely a single offline plan: weather changes, road delays, temporary communication degradation and urgent reinspection events can invalidate an initially feasible schedule.

The initial project concept already contained a mixed-integer model, ALNS solver and PINN-based energy prediction. The key limitation was that a point energy prediction still behaves like a deterministic parameter once it enters the optimizer. A schedule can therefore look efficient in the model while containing sorties that are unsafe under predictive uncertainty. The second limitation was objective design. Makespan minimization is necessary, but it is not sufficient when high-risk towers should be inspected earlier than low-value tasks. The third limitation was operational: a static plan cannot use new information during the execution horizon.

This paper addresses these limitations with UQ-RV-ALNS. The method is deliberately conservative. It does not claim exact optimality or field validation. Instead, it asks whether an uncertainty-aware and value-aware scheduling layer can improve the operational evidence chain needed for a Transportation Research Part E style manuscript.

The contributions are threefold. First, the paper converts a point PINN-style energy estimate into a probabilistic scheduling interface, so uncertainty changes dispatch feasibility instead of being reported only after optimization. Second, it introduces a risk-value objective for inspection tasks, aligning routing decisions with defect-priority logic rather than pure makespan. Third, it evaluates event-triggered rolling replanning against static and periodic policies under disturbance events, with all simulation data stored in a reusable audit structure.

## 2. Literature review

The flying-sidekick traveling salesman problem established a canonical optimization model for drone-assisted delivery \cite{murray2015flying}. Recent TRE papers extend this family in several directions: energy supply logistics with aerial and ground vehicles \cite{kim2026bidirectional}, eVTOL-drone routing with no-fly zones and reinforcement learning \cite{liu2026evtol}, air-ground multimodal integration \cite{zhang2026airground}, automatic heuristic design for vehicle-drone routing \cite{shi2026llm}, and synchronized order splitting with truck-drone fleets \cite{yang2025integrated}. These studies show that current routing research values scale, operational realism and solver efficiency.

Adaptive large neighborhood search remains attractive for large routing variants because destroy and repair operators can absorb heterogeneous constraints without requiring every operational detail to be solved exactly \cite{ropke2006alns}. Physics-informed neural networks provide a way to embed physical residuals into learned surrogates \cite{raissi2019pinn}, but using a PINN only as a point predictor does not solve decision risk. This paper therefore uses a probabilistic surrogate interface: the optimizer receives both expected energy and an uncertainty-adjusted upper bound.

## 3. Problem description

Let \(T\) be the set of inspection tasks, \(P\) the set of vehicle stopping points, \(D\) the set of UAVs and \(V\) the set of ground vehicles. Each task \(i \in T\) has a location, service time \(s_i\), risk score \(r_i\) and value \(v_i\). A vehicle can stop at \(p \in P\), launch a UAV to inspect task \(i\), and recover the UAV at the same stop. The synthetic generator creates corridor-like tower coordinates, road-side stopping points, wind and temperature states, UAV battery capacity and disturbance events.

The core decision is to assign each task to a stop and UAV sequence while minimizing a composite operational objective:

\[
\min \; C_{\max} + \lambda_E \sum_i \hat E_i + \lambda_R \sum_i r_i v_i C_i + \lambda_M \sum_i m_i,
\]

where \(C_{\max}\) is makespan, \(\hat E_i\) is predicted sortie energy, \(C_i\) is the completion time of task \(i\), and \(m_i\) is a missed or infeasible-task penalty.

## 4. Probabilistic energy interface

The energy surrogate returns a mean and uncertainty estimate for each candidate sortie:

\[
\hat E_i = \mu_E(x_i;\theta), \qquad \sigma_i = \sigma_E(x_i;\theta),
\]

where \(x_i\) contains distance, wind speed, wind direction, payload, temperature and service-time features. A physically informed loss can be written as:

\[
\mathcal L = \mathcal L_\text{data} + \alpha \mathcal L_\text{physics} + \beta \mathcal L_\text{cal},
\]

with data fit, physical residual and calibration terms. The scheduling layer uses the chance-constrained surrogate:

\[
\mu_E(x_i) + z_\epsilon \sigma_E(x_i) \leq B_d(1-\rho),
\]

where \(B_d\) is UAV battery capacity and \(\rho\) is the reserve ratio. If a sortie violates this bound but remains near the reserve limit, UQ-RV-ALNS applies a conservative sortie mode, representing slower flight, additional reserve management or a micro-stop/recharge action. This action reduces violation risk at a small duration cost.

![Energy uncertainty interface](../04_manuscript_figures/manuscript_Fig2_energy_uq_interface.png)

## 5. UQ-RV-ALNS algorithm

UQ-RV-ALNS combines risk-value task ordering, uncertainty-aware stop selection and event-triggered replanning. The destroy-repair logic follows the ALNS principle but avoids accepting local search moves that delay high-risk, high-value tasks without a compensating feasibility benefit.

Algorithm 1. UQ-RV-ALNS:

1. Generate or update scenario state from towers, stops, weather and battery state.
2. Estimate \(\mu_E, \sigma_E\) for candidate same-stop sortie patterns.
3. Rank tasks by \(v_i(1+2r_i)\) and select stops by q95 energy, duration and infeasibility penalty.
4. Build a multi-UAV schedule using earliest-available assignment.
5. Apply conservative sortie mode for near-boundary q95 violations.
6. Evaluate makespan, expected energy, risk-weighted completion time and violation rate.
7. When an online event exceeds a threshold, warm-start from the current plan and reoptimize affected tasks.

![Workflow](../04_manuscript_figures/manuscript_Fig1_workflow.png)

## 6. Experimental design

The experiments use synthetic corridor scenarios at S, M and L scales. Each experiment stores raw CSV data, summary CSV/Markdown files, source data for figures, and rendered figures. Methods include nearest routing, random feasible assignment, GA-style and ACO-style constructive baselines, fixed ALNS, point-PINN ALNS, UQ-ALNS, RV-ALNS and UQ-RV-ALNS.

The experiment matrix is:

- E1: small-instance reference comparison.
- E2: core method comparison.
- E3: low/medium/high uncertainty robustness.
- E4: value-objective ablation.
- E5: static, periodic and event-triggered online replanning.
- E6: scalability over S/M/L instances.

## 7. Results

### 7.1 Core comparison

UQ-RV-ALNS has the lowest risk-weighted completion time among the main baselines in the core comparison. Relative to nearest routing, it reduces risk-weighted completion time by 37.5%. Relative to point-PINN ALNS, the reduction is 0.5% and top-risk coverage improves by 4.7 percentage points. The makespan change relative to point-PINN ALNS is 0.13%.

![Core comparison](../04_manuscript_figures/manuscript_Fig3_core_comparison.png)

### 7.2 Robustness under uncertainty

Under high uncertainty, point-PINN ALNS has a mean infeasible-sortie rate of 0.75%. UQ-RV-ALNS reduces this to 0.00% by using conservative q95 feasibility and mitigation. The makespan change is 0.24%, which is the expected cost of reliability.

![Uncertainty robustness](../04_manuscript_figures/manuscript_Fig4_uncertainty_robustness.png)

### 7.3 Value-objective ablation

The value-aware component is mainly responsible for top-risk coverage. UQ alone protects feasibility but does not improve task priority as much as the risk-value objective.

![Value ablation](../04_manuscript_figures/manuscript_Fig5_value_ablation.png)

### 7.4 Online replanning

Static plans suffer from disturbed-operation penalties. Event-triggered replanning reduces disturbed makespan by 5.1% relative to static planning and reduces the simulated infeasible-sortie rate from 0.60% to 0.00%. Its average response time is 1.12, compared with 2.60 for periodic replanning.

![Online replanning](../04_manuscript_figures/manuscript_Fig6_online_replanning.png)

### 7.5 Scalability

At L scale, UQ-RV-ALNS has a runtime ratio of 0.12 relative to point-PINN ALNS and reports a descriptive 3.0-percentage-point top-risk coverage increase. The runtime result reflects the present implementation choice: the final UQ-RV variant prioritizes a direct risk-value construction plus conservative feasibility action rather than a heavy local-search pass.

![Scalability](../04_manuscript_figures/manuscript_Fig7_scalability.png)

## 8. Discussion

The results support a bounded claim. The proposed framework is not uniformly better on every metric. Its strength is the combination of value prioritization and reliability protection. It gives up a small amount of makespan in high-uncertainty settings to reduce violations, and it deliberately schedules high-risk tasks earlier. This is a defensible operational tradeoff for inspection, where missing or delaying a high-risk tower can be more consequential than adding a small travel or time cost.

The main limitation is data realism. The present experiments are synthetic simulations with plausible corridor geometry and weather-sensitive energy functions. They are useful for algorithmic validation and manuscript development, but they do not replace field logs, real defect labels, airspace constraints or verified battery degradation data.

Relative to the five reference TRE papers, the present draft is strongest in methodological coupling: it combines energy uncertainty, inspection value and online replanning in one route-construction loop. It is weaker in empirical grounding because the reference papers are framed around richer operational case settings or broader transport-system abstractions. The intended submission claim is therefore an algorithmic contribution for infrastructure inspection, not a validated deployment system.

## 9. Conclusion

This paper reframes vehicle-UAV transmission-line inspection as an uncertainty-aware and risk-value aware operational scheduling problem. By coupling probabilistic energy prediction, chance-constrained feasibility, risk-value task ordering and event-triggered replanning, UQ-RV-ALNS provides a stronger evidence chain than deterministic makespan-only scheduling. The current simulation results are sufficient for a manuscript draft and for identifying the next evidence gap: real or higher-fidelity flight logs are needed before making deployment claims.

## CRediT author statement

To be completed by the authors.

## Declaration of competing interest

The authors declare no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Data availability

All synthetic data, scripts, source CSVs and figures used in the current draft are stored in the local project folders. The generated evidence should be cited as simulation data.

## References

Kim, H., Sari Darmawi Purba, D., & Kontou, E. (2026). Bidirectional energy supply logistics using uncrewed electric aerial and ground vehicles. Transportation Research Part E, 209, 104726.

Liu, S., Yu, Y., Tian, Q., & Sun, H. (2026). Routing optimization for an eVTOL-and-drone delivery system in continuous space with no-fly zones. Transportation Research Part E, 209, 104741.

Zhang, Y., Yang, C., Xi, H., Peng, S., Yang, J., Gan, M., Liu, X., & Ai, R. (2026). Air-ground multimodal transport planning for joint passenger mobility and parcel delivery. Transportation Research Part E, 210, 104825.

Shi, H., & Zhen, L. (2026). LLM-based automatic heuristic design for vehicle-drone collaborative routing problems. Transportation Research Part E, 209, 104760.

Yang, R., & Li, X. (2025). Integrated order splitting, allocation, and delivery problem with a synchronized truck and drone fleet. Transportation Research Part E, 202, 104217.

Murray, C. C., & Chu, A. G. (2015). The flying sidekick traveling salesman problem. Transportation Research Part C, 54, 86-109.

Ropke, S., & Pisinger, D. (2006). An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. Transportation Science, 40(4), 455-472.

Raissi, M., Perdikaris, P., & Karniadakis, G. E. (2019). Physics-informed neural networks. Journal of Computational Physics, 378, 686-707.
