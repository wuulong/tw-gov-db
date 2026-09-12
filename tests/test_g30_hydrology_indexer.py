#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G50 全政府水系流域與水情測站維度器自動化單元測試 (CGS v2.4)
"""

import sys
import json
import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = PROJECT_ROOT / "src" / "modules" / "g30_hydrology_indexer"
PYTHON_BIN = "/Users/wuulong/opt/anaconda3/envs/m2504/bin/python"

if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from river_topology import RiverTopologyEngine


class TestG30HydrologyIndexer(unittest.TestCase):

    def setUp(self):
        self.engine = RiverTopologyEngine()

    def test_river_topology_ancestors_and_descendants(self):
        """測試 1: 親緣鏈祖先追溯與發源支流子樹展開"""
        r = self.engine.get_river("南勢溪")
        self.assertIsNotNone(r)
        self.assertEqual(r["river_code"], "114021")

        # 祖先追溯 (淡水河 -> 新店溪 -> 南勢溪)
        ancestors = self.engine.get_ancestors("114021")
        self.assertGreaterEqual(len(ancestors), 3)
        codes = [a["river_code"] for a in ancestors]
        self.assertEqual(codes, ["114000", "114020", "114021"])

        # 發源支流展開
        descendants = self.engine.get_descendants("114021")
        self.assertGreater(len(descendants), 0)
        d_names = [d["river_name"] for d in descendants]
        self.assertIn("桶後溪", d_names)

    def test_search_rivers_filters(self):
        """測試 2: 多維度水脈檢索 (官方過濾、流域過濾)"""
        # 官方過濾
        res_off = self.engine.search_rivers(basin="頭前溪", official_only=True)
        for r in res_off:
            self.assertEqual(r["is_civilian"], 0)

        # 關鍵字檢索
        res_kw = self.engine.search_rivers(keyword="鹿寮坑溪")
        self.assertGreater(len(res_kw), 0)
        self.assertIn("130000", res_kw[0]["topology_path"])

    def test_stations_anchoring(self):
        """測試 3: 測站沿親緣拓樸關聯"""
        stations = self.engine.get_stations_for_river("114021")
        s_names = [s["station_name"] for s in stations]
        self.assertIn("烏來雨量站", s_names)
        self.assertIn("新店溪秀朗橋水位站", s_names)

    def test_cli_commands(self):
        """測試 4: g50_cli 常用命令與純淨 JSON 輸出"""
        cli_path = MODULE_DIR / "g30_cli.py"

        # status
        p = subprocess.run([PYTHON_BIN, str(cli_path), "status", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        data = json.loads(p.stdout)
        self.assertEqual(data["module"], "g30_hydrology_indexer")
        self.assertGreater(data["total_rivers"], 1000)

        # search
        p = subprocess.run([PYTHON_BIN, str(cli_path), "search", "頭前溪", "-l", "2", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        items = json.loads(p.stdout)
        self.assertLessEqual(len(items), 2)

        # trace
        p = subprocess.run([PYTHON_BIN, str(cli_path), "trace", "南勢溪", "-j"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        trace_data = json.loads(p.stdout)
        self.assertEqual(trace_data[0]["river_name"], "淡水河")

    def test_hydrate_pipe_streaming(self):
        """測試 5: WRA-Civ JSONL 串流管線記憶體注入 plugins.gov_db"""
        cli_path = MODULE_DIR / "g30_cli.py"
        sample_jsonl = json.dumps({
            "river_code": "114021",
            "river_name": "南勢溪",
            "plugins": {"gis": {"confluence_lon": 121.5}}
        }) + "\n"

        p = subprocess.run([PYTHON_BIN, str(cli_path), "hydrate"], input=sample_jsonl, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        hydrated = json.loads(p.stdout.strip())
        self.assertIn("plugins", hydrated)
        self.assertIn("gov_db", hydrated["plugins"])
        self.assertEqual(hydrated["plugins"]["gov_db"]["river_office"], "第十河川分署")
        self.assertGreater(hydrated["plugins"]["gov_db"]["associated_stations_count"], 0)


if __name__ == "__main__":
    unittest.main()
