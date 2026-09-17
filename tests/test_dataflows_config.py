"""Config isolation: get/set must not leak nested-dict references."""

import copy
import unittest

import pytest

import tradingagents.default_config as default_config
from tradingagents.dataflows.config import get_config, set_config


@pytest.mark.unit
class DataflowsConfigIsolationTests(unittest.TestCase):
    def setUp(self):
        set_config(copy.deepcopy(default_config.DEFAULT_CONFIG))

    def test_get_config_returns_deep_copy(self):
        cfg = get_config()
        cfg["data_vendors"]["core_stock_apis"] = "online_api"
        cfg["tool_vendors"]["get_observations"] = "online_api"

        fresh = get_config()
        self.assertEqual(fresh["data_vendors"]["core_stock_apis"], "local_csv")
        self.assertNotIn("get_observations", fresh["tool_vendors"])

    def test_set_config_does_not_alias_caller_nested_dicts(self):
        custom = copy.deepcopy(default_config.DEFAULT_CONFIG)
        custom["data_vendors"]["core_stock_apis"] = "online_api"
        custom["tool_vendors"]["get_observations"] = "online_api"

        set_config(custom)

        custom["data_vendors"]["core_stock_apis"] = "local_csv"
        custom["tool_vendors"]["get_observations"] = "local_csv"

        fresh = get_config()
        self.assertEqual(fresh["data_vendors"]["core_stock_apis"], "online_api")
        self.assertEqual(fresh["tool_vendors"]["get_observations"], "online_api")

    def test_partial_nested_update_preserves_existing_defaults(self):
        set_config(
            {
                "data_vendors": {
                    "core_stock_apis": "online_api",
                }
            }
        )

        fresh = get_config()
        self.assertEqual(fresh["data_vendors"]["core_stock_apis"], "online_api")
        self.assertEqual(fresh["data_vendors"]["technical_indicators"], "local_csv")
        self.assertEqual(fresh["data_vendors"]["fundamental_data"], "local_csv")
        self.assertEqual(fresh["data_vendors"]["news_data"], "local_csv")

    def test_nested_dict_updates_merge_one_level_deep(self):
        set_config({"tool_vendors": {"get_observations": "online_api"}})
        set_config({"tool_vendors": {"get_weather_warning": "local_csv"}})

        fresh = get_config()
        self.assertEqual(fresh["tool_vendors"]["get_observations"], "online_api")
        self.assertEqual(fresh["tool_vendors"]["get_weather_warning"], "local_csv")
