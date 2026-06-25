import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.candidate_stops import (
    generate_clustered_stops,
    screen_service_pairs,
    with_candidate_stops,
)
from uqrv.energy import EnergyModel
from uqrv.proposal_design import generate_proposal_scenario


class CandidateStopTests(unittest.TestCase):
    def test_kmeans_candidate_stops_are_deterministic_and_cover_all_towers(self):
        scenario = generate_proposal_scenario("M", variant_index=1, seed=2, uncertainty="medium")
        first = generate_clustered_stops(scenario.towers, target_count=10, method="kmeans", seed=31)
        second = generate_clustered_stops(scenario.towers, target_count=10, method="kmeans", seed=31)
        self.assertEqual(len(first.stops), 10)
        self.assertEqual([(s.x, s.y) for s in first.stops], [(s.x, s.y) for s in second.stops])
        self.assertEqual(set(first.assignments), {tower.id for tower in scenario.towers})
        self.assertTrue(all(size > 0 for size in first.cluster_sizes.values()))
        self.assertEqual(first.method, "kmeans")

    def test_density_candidate_stops_merge_corridor_groups_and_cover_all_towers(self):
        scenario = generate_proposal_scenario("S", variant_index=2, seed=4, uncertainty="low")
        stop_set = generate_clustered_stops(
            scenario.towers,
            target_count=8,
            method="dbscan",
            eps=3.5,
            min_samples=2,
            seed=5,
        )
        self.assertGreater(len(stop_set.stops), 0)
        self.assertLessEqual(len(stop_set.stops), 8)
        self.assertEqual(set(stop_set.assignments), {tower.id for tower in scenario.towers})
        self.assertEqual(sum(stop_set.cluster_sizes.values()), len(scenario.towers))
        self.assertEqual(stop_set.method, "dbscan")

    def test_service_pair_screening_reduces_pairs_and_keeps_each_tower_reachable(self):
        scenario = generate_proposal_scenario("M", variant_index=0, seed=6, uncertainty="high")
        stop_set = generate_clustered_stops(scenario.towers, target_count=8, method="kmeans", seed=7)
        clustered = with_candidate_stops(scenario, stop_set)
        screen = screen_service_pairs(
            clustered,
            clustered.stops,
            EnergyModel(clustered.battery_capacity),
            nearest_per_tower=3,
            use_quantile=True,
        )
        self.assertEqual(screen.total_pairs, len(clustered.towers) * len(clustered.stops))
        self.assertLess(screen.screened_pair_count, screen.total_pairs)
        self.assertEqual({pair.tower_id for pair in screen.pairs}, {tower.id for tower in clustered.towers})
        self.assertTrue(all(count <= 3 for count in screen.by_tower_counts.values()))
        self.assertGreater(screen.reduction_ratio, 0.0)

    def test_with_candidate_stops_preserves_scenario_metadata_except_stops(self):
        scenario = generate_proposal_scenario("S", variant_index=0, seed=1)
        stop_set = generate_clustered_stops(scenario.towers, target_count=4, method="kmeans", seed=3)
        clustered = with_candidate_stops(scenario, stop_set)
        self.assertEqual(len(clustered.stops), 4)
        self.assertEqual(clustered.towers, scenario.towers)
        self.assertEqual(clustered.vehicle_count, scenario.vehicle_count)
        self.assertIn("kmeans4", clustered.id)


if __name__ == "__main__":
    unittest.main()
