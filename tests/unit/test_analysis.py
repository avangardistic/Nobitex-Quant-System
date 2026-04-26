import json

from analysis.comparator import compare_runs
from analysis.reporter import write_csv_report, write_html_report, write_json_report
from analysis.stats_calculator import trade_stats
from analysis.visualizer import equity_chart_payload


def test_analysis_helpers(tmp_path):
    payload = {"metrics": {"a": 1}, "trust": {"reproducibility_hash": "x"}, "trades": [{"pnl": 1}]}
    assert trade_stats(payload["trades"])["win_rate"] == 1
    assert compare_runs(payload, payload)["trust_hash_equal"]
    assert write_json_report(tmp_path / "report.json", payload).exists()
    assert write_csv_report(tmp_path / "report.csv", payload["trades"]).exists()
    assert write_html_report(tmp_path / "report.html", payload).exists()
    assert equity_chart_payload(__import__("pandas").Series([1, 2]))["y"] == [1.0, 2.0]
