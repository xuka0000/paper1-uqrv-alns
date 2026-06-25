import sys
import unittest
from pathlib import Path
from random import Random

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.alns_operators import (
    AdaptiveOperatorWeights,
    SimulatedAnnealingAcceptance,
    energy_minimum_insert_repair,
    greedy_insert_repair,
    random_removal,
    synchronization_aware_insert_repair,
    worst_energy_removal,
)
from uqrv.energy import EnergyModel
from uqrv.scenario import Scenario, Stop, Tower, Weather, generate_scenario


class AlnsOperatorTests(unittest.TestCase):
    def test_random_destroy_removes_requested_unique_towers(self):
        scenario = generate_scenario(size="S", seed=20)
        move = random_removal(scenario.towers, remove_count=3, rng=Random(1))

        self.assertEqual(move.operator, "random_removal")
        self.assertEqual(len(move.removed), 3)
        self.assertEqual(len(move.kept), len(scenario.towers) - 3)
        all_ids = [tower.id for tower in move.kept + move.removed]
        self.assertEqual(sorted(all_ids), sorted(tower.id for tower in scenario.towers))
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_worst_energy_removal_targets_high_energy_tower(self):
        scenario = generate_scenario(size="S", seed=21, uncertainty="high")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)
        move = worst_energy_removal(scenario.towers, scenario, energy, remove_count=2)

        nearest_energy = {}
        for tower in scenario.towers:
            stop = min(scenario.stops, key=lambda s: (s.x - tower.x) ** 2 + (s.y - tower.y) ** 2)
            nearest_energy[tower.id] = energy.estimate(stop, tower, scenario.weather).q95_energy
        highest_energy_tower = max(nearest_energy, key=nearest_energy.get)

        self.assertEqual(move.operator, "worst_energy_removal")
        self.assertIn(highest_energy_tower, {tower.id for tower in move.removed})

    def test_greedy_repair_reconstructs_sequence_without_duplicates(self):
        scenario = generate_scenario(size="S", seed=22)
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)
        move = random_removal(scenario.towers, remove_count=4, rng=Random(2))

        repaired = greedy_insert_repair(move.kept, move.removed, scenario, energy, use_quantile=True)

        repaired_ids = [tower.id for tower in repaired]
        self.assertEqual(sorted(repaired_ids), sorted(tower.id for tower in scenario.towers))
        self.assertEqual(len(repaired_ids), len(set(repaired_ids)))

    def test_energy_minimum_repair_prioritizes_low_q95_towers(self):
        scenario = _simple_repair_scenario(
            [
                Tower(0, 1.0, 0.0, 0.2, 40.0, 4.0, 0.8, 0),
                Tower(1, 4.0, 0.0, 0.2, 40.0, 4.0, 0.8, 0),
                Tower(2, 8.0, 0.0, 0.2, 40.0, 4.0, 0.8, 0),
            ]
        )
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)

        repaired = energy_minimum_insert_repair([], scenario.towers, scenario, energy, use_quantile=True)

        self.assertEqual([tower.id for tower in repaired], [0, 1, 2])

    def test_energy_minimum_repair_tie_breaks_by_unified_priority(self):
        scenario = Scenario(
            id="repair_priority_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 0.0, 0.0, risk=1.0, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 0.0, 0.0, risk=0.0, value=20.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        energy = EnergyModel(battery_capacity=scenario.battery_capacity, reserve_ratio=0.0)

        repaired = energy_minimum_insert_repair([], scenario.towers, scenario, energy, use_quantile=True)

        self.assertEqual([tower.id for tower in repaired], [1, 0])

    def test_synchronization_aware_repair_interleaves_corridor_segments(self):
        towers = [
            Tower(0, 1.0, 0.0, 0.2, 40.0, 4.0, 0.8, 0),
            Tower(1, 2.0, 0.0, 0.2, 40.0, 4.0, 0.8, 0),
            Tower(2, 3.0, 0.0, 0.2, 40.0, 4.0, 0.8, 0),
            Tower(3, 1.0, 8.0, 0.2, 40.0, 4.0, 0.8, 1),
            Tower(4, 2.0, 8.0, 0.2, 40.0, 4.0, 0.8, 1),
            Tower(5, 1.0, 16.0, 0.2, 40.0, 4.0, 0.8, 2),
        ]
        scenario = _simple_repair_scenario(towers)
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)

        repaired = synchronization_aware_insert_repair([], scenario.towers, scenario, energy, use_quantile=True)
        segments = [tower.segment for tower in repaired]

        self.assertEqual(sorted(tower.id for tower in repaired), list(range(6)))
        self.assertEqual(len(set(segments[:3])), 3)
        self.assertLessEqual(_max_segment_run(segments), 2)

    def test_adaptive_operator_weights_update_and_normalize(self):
        weights = AdaptiveOperatorWeights(["random", "worst"], reaction=0.5)
        before = weights.probabilities()["random"]

        weights.update("random", score=10.0)
        probs = weights.probabilities()

        self.assertGreater(probs["random"], before)
        self.assertAlmostEqual(sum(probs.values()), 1.0)
        self.assertIn(weights.select(Random(0)), {"random", "worst"})
        self.assertEqual(weights.stats["random"].uses, 1)

    def test_simulated_annealing_acceptance_accepts_improvements_and_rejects_bad_moves(self):
        acceptance = SimulatedAnnealingAcceptance(initial_temperature=1.0, cooling_rate=0.5)

        self.assertTrue(acceptance.accept(current=10.0, candidate=9.0, rng=Random(0)))
        self.assertFalse(acceptance.accept(current=10.0, candidate=1000.0, rng=Random(0)))
        acceptance.cool()
        self.assertAlmostEqual(acceptance.temperature, 0.5)


def _simple_repair_scenario(towers):
    return Scenario(
        id="repair_unit",
        size="S",
        seed=0,
        towers=towers,
        stops=[Stop(0, 0.0, 0.0), Stop(1, 0.0, 8.0), Stop(2, 0.0, 16.0)],
        vehicle_count=1,
        uav_count=2,
        vehicle_speed_kmph=65.0,
        drone_speed_kmph=46.0,
        battery_capacity=150.0,
        weather=Weather(1.0, 0.0, 22.0, 0.08),
    )


def _max_segment_run(segments):
    longest = 0
    current = 0
    previous = None
    for segment in segments:
        current = current + 1 if segment == previous else 1
        previous = segment
        longest = max(longest, current)
    return longest


if __name__ == "__main__":
    unittest.main()
