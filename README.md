# SignalForge v2.0

**Reasoning as a Service** — An autonomous AI agent that sells its thinking.

Scans Polymarket markets, analyzes with DGrid AI, sizes positions with Kelly Criterion, anchors every reasoning trace on Arc, and settles trades with real USDC transfers. Users subscribe to signals, pay per-signal via Circle Nanopayments, and can copy-trade the agent's recommendations.

Built for the [Agora Agents Hackathon](https://agora.thecanteenapp.com/) by Canteen × Circle × Arc.

## Why SignalForge

| Problem | Solution |
|---------|----------|
| Prediction market agents are unmonetized | Subscription model — $0.01/signal via Circle Nanopayments |
| AI decisions are black boxes | Every reasoning trace hashed and anchored on Arc (~$0.01/tx) |
| Copy-trading is blind | Users see full reasoning before copying |
| Cross-chain capital is fragmented | Circle Gateway unified balance across chains |
| Gas fees eat into small trades | Arc charges ~$0.01 in USDC, not volatile tokens |
| Live vs paper is unclear | Real USDC settlement on Arc in live mode — verifiable on-chain |

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Frontend (Next.js)                 │
│  Dashboard · Signals · Terminal · Subscriptions │
└──────────────────┬──────────────────────────────┘
                   │ REST API
┌──────────────────▼──────────────────────────────┐
│              FastAPI Backend                    │
│                                                 │
│  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ Scout Agent │  │  DGrid AI Analyst        │  │
│  │ Polymarket  │→ │  200+ models via DGrid   │  │
│  │ + News RSS  │  │  Structured reasoning    │  │
│  └─────────────┘  └────────────┬─────────────┘  │
│                                │                │
│  ┌─────────────┐  ┌───────────▼──────────────┐  │
│  │ Signal Eng  │  │  Executor Agent          │  │
│  │ Kelly Calc  │→ │  - Anchor on Arc         │  │
│  │ Edge detect │  │  - USDC settlement (live)│  │
│  └─────────────┘  │  - Notify subscribers    │  │
│                   │  - Collect nanopayments  │  │
│                   └───────────┬──────────────┘  │
│                               │                 │
│  ┌────────────────────────────▼──────────────┐  │
│  │  Circle Ecosystem                         │  │
│  │  ┌─────────┐ ┌─────────┐ ┌────────────┐   │  │
│  │  │ Wallets │ │ Gateway │ │Nanopayments│   │  │
│  │  │ SDK     │ │Unified  │ │$0.01/signal│   │  │
│  │  └─────────┘ └─────────┘ └────────────┘   │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Arc Blockchain                           │  │
│  │  - Trace anchoring (~$0.01/tx)            │  │
│  │  - USDC settlement (live: $0.10/trade)    │  │
│  │  - Verifiable on ArcScan                  │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  ┌───────────────────────────────────────────┐  │
│  │  Subscription Manager                     │  │ 
│  │  - User subscriptions                     │  │
│  │  - Per-signal nanopayments                │  │
│  │  - Copy-trade tracking                    │  │
│  │  - Revenue analytics                      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **AI** | DGrid AI Gateway (OpenAI-compatible, 200+ models) |
| **Backend** | Python 3.12, FastAPI, httpx, web3.py |
| **Frontend** | Next.js 16, React 19, Tailwind CSS 3, wagmi/viem |
| **Blockchain** | Arc Testnet (Circle's L1), USDC settlement |
| **Circle** | Wallets SDK, Gateway, Nanopayments, USDC |
| **Data** | Polymarket Gamma API + CLOB API, BBC RSS feeds |
| **Deployment** | Render (backend), Vercel (frontend) |

## Circle Integration

| Product | Status | Usage |
|---------|--------|-------|
| **Arc** | Integrated | Trace anchoring, USDC gas, live settlement |
| **USDC** | Integrated | Native gas + trade settlement ($0.10/trade live) |
| **Wallets SDK** | Integrated | Dev-controlled wallet management |
| **Gateway** | Integrated | Unified balance, cross-chain transfers |
| **Nanopayments** | Integrated | Per-signal micropayments ($0.01) |
| **CCTP** | Planned | Cross-chain USDC bridging (mainnet) |
| **Paymaster** | Planned | Gasless UX (mainnet) |
| **USYC** | Planned | Yield on idle capital (mainnet) |
| **App Kit** | Planned | Bridge, Swap, Send components (mainnet) |

## Quick Start

### 1. Configure

```bash
cd signalforge
cp .env.example .env
# Edit .env with your keys
```

### 2. Backend

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn agents.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

### 4. Run

```bash
# One analysis cycle
curl -X POST http://localhost:8000/api/cycle

# Subscribe to signals
curl -X POST http://localhost:8000/api/subscribe \
  -H 'Content-Type: application/json' \
  -d '{"user_address": "0x..."}'

# View agent activity logs
curl http://localhost:8000/api/logs

# Check subscription stats
curl http://localhost:8000/api/subscriptions/stats
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/config` | Current agent config |
| PUT | `/api/config` | Update config (instant refetch) |
| POST | `/api/agent/start` | Start auto-cycling |
| POST | `/api/agent/stop` | Stop auto-cycling |
| GET | `/api/agent/status` | Full status (Arc, Circle, subs) |
| POST | `/api/cycle` | Run one analysis cycle |
| GET | `/api/signals` | Current signals |
| GET | `/api/trades` | Trade history with Arc tx links |
| GET | `/api/portfolio` | Portfolio summary |
| POST | `/api/subscribe` | Subscribe to signals ($0.01/signal) |
| GET | `/api/subscriptions` | List active subscribers |
| GET | `/api/subscriptions/stats` | Subscription analytics |
| GET | `/api/circle-stack` | Circle product status |
| GET | `/api/logs` | Agent activity logs |
| POST | `/api/seed` | Load demo signals |

## How It Works

### 1. Scan
ScoutAgent fetches 50 active Polymarket markets (sorted by volume) + recent news headlines from BBC RSS.

### 2. Analyze
DGridAnalyst sends each market to DGrid AI with a structured prompt. The LLM returns:
- Estimated true probability
- Confidence level
- BUY_YES / BUY_NO / SELL_YES / SELL_NO / HOLD recommendation
- Key factors and risks
- Full reasoning text

### 3. Signal
Signal engine computes:
- Edge = |AI probability - market price|
- Kelly Criterion position sizing
- Risk-adjusted confidence thresholds
- Filters by min EV and min confidence

### 4. Execute & Monetize
ExecutorAgent:
- Hashes the reasoning trace (SHA-256)
- Anchors the hash on Arc via self-transaction (~$0.01)
- **Live mode**: transfers $0.10 USDC on Arc as trade settlement (verifiable on ArcScan)
- **Paper mode**: simulated trade with Arc trace only
- Notifies subscribers and collects nanopayments
- Tracks PnL, copy-trades, and revenue

## Paper vs Live Mode

| Feature | Paper Mode | Live Mode |
|---------|-----------|-----------|
| AI Analysis | ✓ Real DGrid AI | ✓ Real DGrid AI |
| Signal Generation | ✓ Kelly Criterion | ✓ Kelly Criterion |
| Arc Trace Anchoring | ✓ Hash on-chain | ✓ Hash on-chain |
| USDC Settlement | ✗ Simulated | ✓ Real $0.10 USDC transfer |
| ArcScan Verification | Trace only | Trace + Settlement tx |

## Subscription Model

- **Price**: $0.01 per signal via Circle Nanopayments
- **Delivery**: Real-time signal push with full reasoning trace
- **Copy-trading**: Users can replicate agent's trades
- **Revenue**: Agent earns from subscriptions
- **Verification**: Every reasoning trace anchored on Arc — permanent, auditable

## Hackathon Alignment

| Criteria | Weight | How SignalForge Delivers |
|----------|--------|-------------------------|
| **Agentic Sophistication** | 30% | AI makes autonomous decisions with full reasoning, executes trades, manages subscriptions, anchors traces |
| **Traction** | 30% | Live subscription model, real users connecting wallets, real USDC settlement on Arc |
| **Circle Tool Usage** | 20% | Wallets SDK, Gateway (unified balance), Nanopayments (per-signal), Arc (anchoring + settlement), USDC (gas) |
| **Innovation** | 20% | "Reasoning as a Service" — traces are the product, not just the trades. Live USDC settlement proves execution. |

## RFB Match

**RFB 02 — Prediction Market Trader Intelligence**
- Find +EV bets across noisy news, data, and sentiment ✓
- Size positions properly (Kelly Criterion) ✓
- Cross-market portfolio construction ✓
- Information source credibility weighting ✓

## License

MIT
