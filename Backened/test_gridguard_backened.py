# -*- coding: utf-8 -*-
"""
GridGuard AI Microgrid Backend Test Suite
Verifies IEEE 1547.4 islanding, 35% SoC contingency shedding, Genset auto-crank, and REST endpoints.
"""

import sys
import os
import unittest
import json

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Backened.microgrid_engine import MicrogridEngine
from Backened.app import app


class TestMicrogridEngine(unittest.TestCase):
    def setUp(self):
        self.engine = MicrogridEngine()
        self.engine.reset()

    def test_nominal_state(self):
        state = self.engine.state
        self.assertFalse(state["isOutageActive"])
        self.assertEqual(state["loads"]["tier1"]["kw"], 112.5)
        self.assertEqual(state["loads"]["tier2"]["kw"], 142.5)
        self.assertEqual(state["loads"]["tier3"]["kw"], 90.8)
        self.assertEqual(state["grid"]["status"], "CONNECTED")
        self.assertGreater(state["solar"]["kw"], 400.0)

    def test_outage_simulation_tier3_shed(self):
        state = self.engine.simulate_outage()
        self.assertTrue(state["isOutageActive"])
        self.assertEqual(state["grid"]["breaker"], "CB-101 TRIPPED OPEN")
        # Tier 3 MUST be completely disconnected (0.0 kW) during outage
        self.assertEqual(state["loads"]["tier3"]["kw"], 0.0)
        # Tier 1 must remain energized
        self.assertEqual(state["loads"]["tier1"]["kw"], 112.5)
        # Tier 2 is energized since default SoC is 88.5% > 35%
        self.assertEqual(state["loads"]["tier2"]["kw"], 142.5)

    def test_strict_35_percent_soc_contingency_rule(self):
        # 1. Start outage
        self.engine.simulate_outage()

        # 2. Simulate SoC dropping below 35% (e.g. 32%)
        state = self.engine.set_soc(32.0)

        # Tier 2 MUST be shed immediately to 0.0 kW to protect Tier 1
        self.assertEqual(state["loads"]["tier2"]["kw"], 0.0)
        self.assertIn("SHED", state["loads"]["tier2"]["status"])
        self.assertEqual(state["loads"]["tier2"]["breaker"], "CB-T2 TRIPPED OPEN")

        # Tier 1 remains 100% energized
        self.assertEqual(state["loads"]["tier1"]["kw"], 112.5)

        # Genset should auto-crank in AUTO mode
        self.assertTrue(state["genset"]["running"])
        self.assertIn("AUTO-RUNNING", state["genset"]["status"])
        self.assertGreater(state["genset"]["powerKW"], 0.0)

    def test_restore_grid(self):
        self.engine.simulate_outage()
        self.engine.set_soc(25.0)  # triggers Tier 2 shed
        state = self.engine.restore_grid()

        self.assertFalse(state["isOutageActive"])
        self.assertEqual(state["grid"]["status"], "CONNECTED")
        # All tiers re-energized
        self.assertEqual(state["loads"]["tier1"]["kw"], 112.5)
        self.assertEqual(state["loads"]["tier2"]["kw"], 142.5)
        self.assertEqual(state["loads"]["tier3"]["kw"], 90.8)
        self.assertFalse(state["genset"]["running"])

    def test_weather_profiles(self):
        state_cloudy = self.engine.set_weather("cloudy")
        self.assertEqual(state_cloudy["currentWeather"], "cloudy")
        self.assertAlmostEqual(state_cloudy["solar"]["kw"], 204.2, places=1)

        state_stormy = self.engine.set_weather("stormy")
        self.assertEqual(state_stormy["currentWeather"], "stormy")
        self.assertAlmostEqual(state_stormy["solar"]["kw"], 58.1, places=1)


class TestFlaskAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("loads", data["data"])

    def test_api_allows_live_server_origin(self):
        resp = self.client.options(
            "/api/status",
            headers={
                "Origin": "http://127.0.0.1:5500",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertIn("http://127.0.0.1:5500", resp.headers["Access-Control-Allow-Origin"])

    def test_dashboard_is_served_from_frontend_folder(self):
        resp = self.client.get("/")
        try:
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"GridGuard", resp.data)
            for section in (
                "dashboard",
                "energy-management",
                "outage-simulation",
                "load-priority",
                "analytics",
            ):
                self.assertIn(f'href="#{section}"'.encode(), resp.data)
                self.assertIn(f'id="{section}"'.encode(), resp.data)
        finally:
            resp.close()

    def test_simulate_outage_endpoint(self):
        resp = self.client.post("/api/outage/simulate")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["data"]["isOutageActive"])
        self.assertEqual(data["data"]["loads"]["tier3"]["kw"], 0.0)

    def test_set_soc_endpoint(self):
        resp = self.client.post("/api/bess/soc", json={"soc": 30.0})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["data"]["bess"]["soc"], 30.0)

    def test_restore_grid_endpoint(self):
        resp = self.client.post("/api/outage/restore")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["data"]["isOutageActive"])

    def test_get_logs_endpoint(self):
        resp = self.client.get("/api/logs?limit=5")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data["logs"], list)


if __name__ == "__main__":
    unittest.main()