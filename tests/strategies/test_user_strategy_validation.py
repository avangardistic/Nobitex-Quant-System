from pathlib import Path

import pytest

from core.exceptions import ValidationError
from strategies.base.validation import validate_strategy_file


def test_user_strategy_validation(tmp_path: Path):
    strategy_file = tmp_path / "my_strategy.py"
    strategy_file.write_text(
        """
import pandas as pd
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy

class MyStrategy(BaseStrategy):
    def calculate_indicators(self, data: pd.DataFrame):
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext):
        if len(context.history) < 2:
            return None
        return Signal(timestamp=context.data.index[context.current_index], symbol=context.symbol, action="buy")
""".strip(),
        encoding="utf-8",
    )
    result = validate_strategy_file(strategy_file)
    assert result["strategy_class"] == "MyStrategy"
    assert result["lookahead_safe"] is True


def test_all_repository_user_strategies_validate():
    user_strategy_dir = Path("strategies/user")
    strategy_files = sorted(
        path for path in user_strategy_dir.glob("*.py") if path.name != "__init__.py"
    )

    assert strategy_files, "Expected at least one user strategy file to validate"

    for strategy_file in strategy_files:
        result = validate_strategy_file(strategy_file)
        assert result["path"] == str(strategy_file)
        assert result["lookahead_safe"] is True
        assert result["replay_matches_after_reset"] is True
        assert result["deterministic_across_instances"] is True


def test_validation_rejects_stateful_strategy_without_reset(tmp_path: Path):
    strategy_file = tmp_path / "bad_stateful.py"
    strategy_file.write_text(
        """
import pandas as pd
from strategies.base.context import StrategyContext
from strategies.base.signal import Signal
from strategies.base.strategy_interface import BaseStrategy

class BadStatefulStrategy(BaseStrategy):
    def __init__(self):
        self.counter = 0

    def calculate_indicators(self, data: pd.DataFrame):
        return {"close": data["close"]}

    def generate_signal(self, context: StrategyContext):
        self.counter += 1
        if self.counter % 2:
            return Signal(timestamp=context.data.index[context.current_index], symbol=context.symbol, action="buy")
        return None
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        validate_strategy_file(strategy_file)
