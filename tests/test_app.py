import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import monitor as app


def payload(value=81.87, station="E_17", measured_at="11/11/2026 22:00"):
    signals = []
    for tag in app.STATIONS[station]["required"]:
        signals.append({
            "tag": tag,
            "valores": [{
                "tag": tag,
                "remota": station,
                "tiempo": measured_at,
                "valor": value,
            }],
        })
    return {"response": {"ok": 1, "codigo": station, "senales": signals}}


def readings_for(station, value=81.87, measured_at="11/11/2026 22:00"):
    return app.parse_response(payload(value, station, measured_at), station)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        with app.DATA_LOCK:
            app.READINGS.clear()
            for status in app.STATION_STATUS.values():
                status["last_success"] = None
                status["last_error"] = None
        app.LAST_ATTEMPT = float("-inf")
        app.LAST_MANUAL = float("-inf")

    def test_parse_validates_station_required_signals_and_values(self):
        self.assertEqual(len(app.parse_response(payload(), "E_17")), 4)
        bad_station = payload()
        bad_station["response"]["codigo"] = "E_18"
        with self.assertRaises(ValueError):
            app.parse_response(bad_station, "E_17")
        missing = payload()
        missing["response"]["senales"].pop()
        with self.assertRaises(ValueError):
            app.parse_response(missing, "E_17")
        invalid = payload()
        invalid["response"]["senales"][0]["valores"][0]["valor"] = None
        with self.assertRaises(ValueError):
            app.parse_response(invalid, "E_17")

    def test_refresh_replaces_previous_measurements_instead_of_accumulating(self):
        with patch.object(
            app, "fetch_readings",
            side_effect=lambda station: readings_for(station, measured_at="11/11/2026 21:00"),
        ):
            self.assertTrue(app.refresh()[0])
        first = app.get_data()
        expected = sum(len(config["required"]) for config in app.STATIONS.values())
        self.assertEqual(len(first["readings"]), expected)
        self.assertEqual(first["readings"][0]["measured_at"], "2026-11-11T21:00")
        self.assertTrue(all(info["last_success"] for info in first["stations"].values()))
        with patch.object(
            app, "fetch_readings",
            side_effect=lambda station: readings_for(station, 82, "11/11/2026 22:00"),
        ):
            self.assertTrue(app.refresh(manual=True)[0])
        second = app.get_data()
        self.assertEqual(len(second["readings"]), expected)
        self.assertNotIn("2026-11-11T21:00", {row["measured_at"] for row in second["readings"]})
        self.assertTrue(all(row["value"] == 82 for row in second["readings"]))

    def test_failure_is_isolated_and_retains_previous_data_until_success(self):
        with patch.object(app, "fetch_readings", side_effect=readings_for):
            app.refresh()

        def partial_failure(station):
            if station == "PN34":
                raise ValueError("fuente inválida")
            return readings_for(station, 82)

        with patch.object(app, "fetch_readings", side_effect=partial_failure):
            self.assertFalse(app.refresh(manual=True)[0])
        result = app.get_data()
        values = {row["tag"]: row["value"] for row in result["latest"]}
        self.assertEqual(values["PN34WIC101"], 81.87)
        self.assertEqual(values["AR21LI__01"], 82)
        self.assertEqual(values["E_18VPCT01"], 82)
        self.assertIn("fuente inválida", result["stations"]["PN34"]["last_error"])
        self.assertIsNone(result["stations"]["AR21"]["last_error"])
        with patch.object(app, "fetch_readings", side_effect=readings_for), patch.object(app, "LAST_MANUAL", float("-inf")):
            app.refresh(manual=True)
        self.assertIsNone(app.get_data()["stations"]["PN34"]["last_error"])

    def test_other_stations_are_validated_independently(self):
        for station in ("PN34", "AR21", "E_18"):
            with self.subTest(station=station):
                result = readings_for(station)
                self.assertEqual({row[0] for row in result}, app.STATIONS[station]["required"])
                malformed = payload(station=station)
                malformed["response"]["senales"][0]["valores"][0]["remota"] = "E_17"
                with self.assertRaises(ValueError):
                    app.parse_response(malformed, station)

    def test_latest_value_comes_from_current_capture(self):
        with patch.object(app, "fetch_readings", side_effect=readings_for):
            app.refresh()
        result = app.get_data()
        latest = {row["tag"]: row["value"] for row in result["latest"]}
        self.assertEqual(latest["E_17VICT01"], 81.87)
        self.assertEqual(len(result["readings"]), sum(
            len(config["required"]) for config in app.STATIONS.values()
        ))

    def test_refresh_interval_and_manual_rate_limit(self):
        with patch.object(app, "fetch_readings", side_effect=readings_for) as fetch:
            self.assertTrue(app.refresh()[0])
            self.assertTrue(app.refresh()[0])
            self.assertEqual(fetch.call_count, len(app.STATIONS))
            self.assertTrue(app.refresh(manual=True)[0])
            self.assertFalse(app.refresh(manual=True)[0])
            self.assertEqual(fetch.call_count, 2 * len(app.STATIONS))

    def test_streamlit_loads_station_data(self):
        with patch.object(app, "fetch_readings", side_effect=readings_for) as fetch:
            page = AppTest.from_file(str(Path(__file__).resolve().parent.parent / "app.py"), default_timeout=20).run()
            self.assertFalse(page.exception)
            self.assertEqual(fetch.call_count, len(app.STATIONS))
            self.assertEqual(len(app.get_data()["latest"]), 9)


if __name__ == "__main__":
    unittest.main()
