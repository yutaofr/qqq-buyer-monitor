import src.backtest as backtest_module


def test_backtest_routes_v11_mode(monkeypatch):
    called = {}

    def fake_run_v11_audit(**kwargs):
        called["kwargs"] = kwargs

    monkeypatch.setattr(backtest_module, "run_v11_audit", fake_run_v11_audit, raising=False)

    rc = backtest_module.main(["--mode", "v11"])

    assert rc == 0
    assert "kwargs" in called
