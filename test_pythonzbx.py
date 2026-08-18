import json
import unittest
from types import SimpleNamespace

from pythonzbx import ACTIVITIES, activity_1, activity_2, activity_6, activity_7, activity_8, activity_5


class FakeClient:
    def call(self, method, params):
        if method == "host.get":
            return [{"hostid": "10001", "host": "Zabbix server"}]
        if method == "item.get":
            return [
                {"itemid": "20001", "name": "CPU utilization", "key_": "system.cpu.util", "value_type": "0"},
                {"itemid": "20002", "name": "CPU utilization nice", "key_": "system.cpu.util[,nice]", "value_type": "0"},
            ]
        if method == "history.get":
            itemids = params["itemids"]
            rows = []
            for itemid in itemids:
                rows.extend([{"itemid": itemid, "clock": "1", "value": "70"}, {"itemid": itemid, "clock": "2", "value": "90"}, {"itemid": itemid, "clock": "3", "value": "80"}])
            return rows[:params["limit"]]
        if method == "trend.get":
            return [{"clock": "1", "num": "60", "value_avg": "75"}]
        if method == "problem.get":
            return [{"eventid": "30001", "severity": "5"}]
        raise AssertionError(method)


class MemoryClient(FakeClient):
    def call(self, method, params):
        if method == "item.get":
            return [
                {"itemid": "20003", "name": "Available memory in %", "key_": "vm.memory.size[pavailable]", "value_type": "0"},
                {"itemid": "20004", "name": "Memory utilization", "key_": "vm.memory.util", "value_type": "0"},
            ]
        if method == "trend.get":
            return [{"clock": "1", "num": "60", "value_avg": "75"}]
        return super().call(method, params)


class ActivitiesTest(unittest.TestCase):
    def setUp(self):
        self.client = FakeClient()
        self.args = SimpleNamespace(host="Zabbix server", limit=1000, minutes=60, threshold=80, window=2)

    def test_all_activities_are_registered(self):
        self.assertEqual(set(ACTIVITIES), set(range(1, 9)))

    def test_cpu_and_feature_engineering(self):
        result = activity_5(self.client, self.args)
        self.assertEqual(result["samples"], 6)
        self.assertEqual(result["cpu_moving_average"], [70.0, 80.0, 85.0, 75.0, 80.0, 85.0])

    def test_activity_1_returns_all_cpu_items(self):
        result = activity_1(self.client, self.args)
        self.assertEqual([item["itemid"] for item in result["items"]], ["20001", "20002"])
        self.assertEqual(len(result["data"]), 6)

    def test_activity_1_limit_is_total(self):
        self.args.limit = 1
        result = activity_1(self.client, self.args)
        self.assertEqual(len(result["data"]), 1)

    def test_activity_2_prefers_memory_utilization(self):
        result = activity_2(MemoryClient(), self.args)
        self.assertEqual(result["item_name"], "Memory utilization")

    def test_dependent_item_preprocessing(self):
        result = activity_6(self.client, SimpleNamespace(raw_latency="rtt=12.75ms"))
        self.assertEqual(result["latency_ms"], 12.75)

    def test_trend_payload_is_json_serializable(self):
        args = SimpleNamespace(host_id="10001", item_ids=["20001"], time_from=1, time_till=2, limit=10)
        result = activity_7(self.client, args)
        json.dumps(result)
        self.assertEqual(result["payload"]["method"], "trend.get")

    def test_webhook_handler_is_available(self):
        self.assertIsNotNone(activity_8)


if __name__ == "__main__":
    unittest.main()