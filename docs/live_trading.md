# Paper Trading and Live Trading

This repository now supports two trading session modes in addition to backtesting:

- `paper`: virtual execution using real or simulated market ticks
- `live`: order placement through the Nobitex API with account-level safety checks

## Important warning

Live trading can place real orders if your environment points at production and valid credentials are configured. Start with paper trading or testnet first.

## Session model

Paper and live commands create lightweight sessions under `reports/paper_trading/` and `reports/live_trading/`.

Each session stores:

- session id
- strategy and symbol
- current status
- report path
- audit or trade history

## Paper trading

Start a paper session:

```bash
quant paper start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000
```

Stop a paper session:

```bash
quant paper stop --session-id <id>
```

List sessions:

```bash
quant paper list
```

Read the saved report:

```bash
quant paper report --session-id <id>
```

Paper mode works without API credentials. By default it uses a deterministic simulated feed unless you extend the session to use market polling or a CSV file.

## Live trading

Start a live session:

```bash
quant live start --strategy MACrossoverStrategy --symbol BTCIRT --capital 10000 --risk 0.01
```

The CLI requires an explicit confirmation prompt before the session starts.

Stop all active live sessions:

```bash
quant live stop --emergency
```

Inspect session status:

```bash
quant live status
```

Inspect current open positions from saved session reports:

```bash
quant live positions
```

## Safety controls

The live trading engine enforces basic controls before an order is placed:

- maximum position size
- maximum daily loss
- risk-per-trade sizing guidance
- emergency stop that requests all active sessions to halt
- audit logging of order placement and cancellation responses

## Required configuration

Relevant `.env` keys:

- `NOBITEX_PAPER_CAPITAL`
- `NOBITEX_PAPER_FEE_RATE`
- `NOBITEX_LIVE_API_KEY`
- `NOBITEX_LIVE_API_SECRET`
- `NOBITEX_LIVE_MAX_POSITION_SIZE`
- `NOBITEX_LIVE_MAX_DAILY_LOSS`
- `NOBITEX_LIVE_RISK_PER_TRADE`
- `NOBITEX_WEBSOCKET_URL`
- `NOBITEX_MARKET_DATA_POLL_SECONDS`

## API permissions

If you use live trading against a real account, the configured key should only have the minimum permissions needed for order placement and status management.

## Limitations

This implementation is intentionally conservative:

- market data uses polling or deterministic simulation rather than a full exchange event stream
- live sessions are safer on testnet first
- paper/live execution does not change backtest engine behavior
