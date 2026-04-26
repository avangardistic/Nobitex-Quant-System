# Nobitex API Reference

Base URLs:
- Production REST: `https://apiv2.nobitex.ir`
- Testnet REST: `https://testnetapiv2.nobitex.ir`
- WebSocket: `wss://ws.nobitex.ir/connection/websocket`

Key endpoints:
- `GET /v3/orderbook/{symbol}`
- `GET /market/udf/history`
- `POST /market/orders/add`
- `POST /market/orders/update-status`
- `GET /users/wallets/list`

The client uses token authentication and a token bucket limiter sized for 300 order actions per 10 minutes by default.
