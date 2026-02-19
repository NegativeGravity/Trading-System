# 🚀 Trading-System
### Institutional-Grade Algorithmic Trading & Backtesting Framework

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue" />
  <img src="https://img.shields.io/badge/Django-5.x-green" />
  <img src="https://img.shields.io/badge/Backtesting-Engine-orange" />
  <img src="https://img.shields.io/badge/Status-Active-success" />
</p>

---

## 📌 Overview

**Trading-System** is a modular, high-performance algorithmic trading and backtesting framework built with Python and Django.

The system is designed to simulate realistic trading conditions while providing a scalable research environment for developing, testing, and analyzing trading strategies.

It consists of:

- 🧠 Intelligent Trading Agents  
- 🏦 High-Fidelity Virtual Broker  
- 🚄 Optimized Historical Data Pipeline  
- 🌐 Interactive Web Dashboard  

The architecture is fully decoupled to allow independent development of strategies, execution logic, and analytics.

---

# 🏗 System Architecture

The project follows a modular architecture:

---

### Component Responsibilities

| Component | Responsibility |
|------------|----------------|
| **Agents** | Generate trading signals (ML / heuristic logic) |
| **Execution Engine** | Coordinate signals and manage trade lifecycle |
| **Virtual Broker** | Simulate order execution & account accounting |
| **Database Layer** | Efficient historical data storage |
| **Django Dashboard** | Visualization, analytics & reporting |

---

# 🧠 Intelligent Trading Engine

The system supports advanced strategy modules including:

### ▸ Machine Learning Based Agents
- Regime detection
- Directional bias prediction
- Noise-robust classification logic

### ▸ Multi-Timeframe Pattern Detection
- Swing Failure Pattern (SFP) detection
- Structure-based reversal setups
- Cross-timeframe confirmation logic

Strategies are fully decoupled from execution to allow safe experimentation.

---

# 🏦 Virtual Broker (High-Fidelity Simulation)

Unlike simple backtesters, the system includes a realistic broker simulation:

### ✔ Intra-Candle Execution Modeling
Simulates price movement inside OHLC candles:


Ensures accurate SL / TP detection.

### ✔ Financial Engine

Real-time calculation of:

- Balance  
- Equity  
- Floating P/L  
- Margin  
- Free Margin  
- Drawdown  

### ✔ Realistic Costs

- Dynamic spreads  
- Commission per lot  
- Slippage modeling  
- Gap handling  

This results in near real-world execution simulation.

---

# 🚄 High-Performance Data Pipeline

Large backtests require efficient storage.

The system uses:

- Zlib compression for historical candle data
- SQLite Binary BLOB storage
- Optimized retrieval pipeline
- Async API serving for large chart datasets

Capable of loading hundreds of thousands of candles efficiently.

---

# 🌐 Django Web Dashboard

The web interface provides:

- Interactive candlestick charts
- Multi-timeframe switching (1m / 5m / 15m / 1h)
- Execution logs synchronized with chart
- Click-to-zoom trade visualization
- Fast client-side aggregation

Built with:

- Django 5.x
- Bootstrap 5
- TradingView Lightweight Charts

---

# 🛠 Tech Stack

### Backend
- Python 3.10+
- Django 5.x
- NumPy
- Pandas
- SciPy

### Frontend
- TradingView Lightweight Charts
- Bootstrap 5

### Storage
- SQLite (compressed BLOB storage)
- Optional PostgreSQL for production

---

# 📥 Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/NegativeGravity/Trading-System.git
cd Trading-System
python -m venv .venv
source .venv/bin/activate
.venv\Scripts\activate

cd web_dashboard
python manage.py makemigrations
python manage.py migrate

python manage.py run_backtest_lorentzian --days 60 --tf 5

python manage.py runserver

http://127.0.0.1:8000
```
