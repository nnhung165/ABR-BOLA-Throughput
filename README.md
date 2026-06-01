# 🎬 BOLA-ABR: Adaptive Bitrate Streaming Simulator

A discrete-event simulation framework for comparing **Adaptive Bitrate (ABR)** streaming algorithms. This project implements and evaluates two control strategies:

- **Predictive Throughput Controller** — selects bitrate based on harmonic-mean bandwidth estimation with a configurable safety margin.
- **BOLA (Buffer Occupancy based Lyapunov Algorithm)** — maximizes a utility-theoretic objective function constrained by real-time playback buffer occupancy.

The simulator includes a **Hybrid Fast-Startup** mechanism that combines throughput estimation during the initial buffer-building phase with Lyapunov optimization during steady-state playback.

---

## 📁 Project Structure

```
BOLA_ABR/
│
├── app.py                      # Streamlit interactive dashboard
├── requirements.txt            # Python dependencies
├── report_analysis.tex         # LaTeX benchmark analysis report
│
├── core/                       # Simulation engine modules
│   ├── __init__.py
│   ├── abr_algorithms.py       # ABR decision logic (ThroughputABR, BolaABR)
│   ├── buffer.py               # Playback buffer dynamics Q(t)
│   ├── metrics.py              # QoE evaluator (rebuffer, smoothness, bitrate)
│   ├── network.py              # Network environment (trace parser, interpolation, jitter)
│   ├── server.py               # Virtual video server (manifest parser, VBR matrix)
│   └── sim_engine.py           # Discrete-event simulation loop (event orchestrator)
│
├── dataset/                    # Sample input data
│   ├── manifest.json           # Sample MPD manifest (video metadata)
│   ├── manifest1.json          # Extended manifest with full VBR chunk data
│   ├── trace.txt               # Sample network bandwidth trace
│   ├── trace1.txt              # Alternative network trace
│   ├── manifests/              # Additional manifest files
│   ├── traces/                 # Additional network trace files
│   └── videos/                 # Video asset directory
│
├── tests/                      # Automated benchmark suite
│   ├── run_benchmarks.py       # Batch benchmark runner (9 scenarios)
│   ├── scenario_configs/       # Test scenario definitions
│   │   ├── test_stable_wifi/   # Stable WiFi 6 Mbps
│   │   ├── testHD/             # High-definition 5 Mbps channel
│   │   ├── test_low_3g/        # Constrained 3G mobile network
│   │   ├── testALTsoft/        # V-shaped bandwidth collapse
│   │   ├── test_alt_hard/      # Square-wave bandwidth oscillation
│   │   ├── testPQ/             # Low-bitrate codec stress
│   │   ├── testHDmanPQtrace/   # HD manifest with poor trace
│   │   ├── badtest/            # Flat single-point trace
│   │   └── testALThard/        # Flat trace with full VBR data
│   ├── test_results/           # Generated CSV logs and comparison plots
│   └── expected_outputs/       # Reference outputs for validation
│
├── test_abr_logic.py           # Unit tests: ABR algorithm decision logic
├── test_env.py                 # Unit tests: Server and Network components
└── test_sim_engine.py          # Integration test: full simulation pipeline
```

### Module Descriptions

| Module | Responsibility |
|:---|:---|
| `abr_algorithms.py` | Implements `BaseABR` (abstract), `ThroughputABR` (harmonic mean + safety margin), and `BolaABR` (Lyapunov objective maximization with reservoir safety check). |
| `buffer.py` | Simulates playback buffer `Q(t)`: tracks depletion during downloads, refill after chunk arrival, and rebuffering events when `Q(t) < download_time`. |
| `metrics.py` | Computes the QoE score: `Ψ = Σ(bitrate) - μ·Σ(|Δbitrate|) - λ·Σ(rebuffer)` with configurable penalty weights. |
| `network.py` | Parses network trace files (1-column or 2-column format), applies linear interpolation between data points, adds stochastic TCP jitter, and supports time-looping for extended simulations. |
| `server.py` | Parses JSON manifests (supports multiple schemas: `Available_Bitrates`, `bitrates`, `bitrates_kbps`), loads pre-computed chunk sizes or generates VBR data via truncated normal distribution. |
| `sim_engine.py` | Orchestrates the discrete-event loop: for each segment, queries ABR for bitrate selection, simulates download over the network, updates buffer state, and logs metrics. |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** (tested with Python 3.13)

### Installation

```bash
# Clone or download the project
cd BOLA_ABR

# Install dependencies
pip install -r requirements.txt
```

### Dependencies

```
numpy>=1.20.0
pandas>=1.3.0
matplotlib>=3.4.0
streamlit>=1.10.0
plotly>=5.0.0
```

---

## 🧪 Running Tests

### 1. Unit Test — ABR Algorithm Logic

Verifies bitrate selection correctness under cold startup, low-buffer, and steady-state conditions.

```bash
python test_abr_logic.py
```

### 2. Unit Test — Server & Network Components

Validates manifest parsing and network trace interpolation.

```bash
python test_env.py
```

### 3. Integration Test — Simulation Engine

Runs a full simulation with a mock network that drops from 6 Mbps to 800 kbps mid-session.

```bash
python test_sim_engine.py
```

### 4. Full Benchmark Suite (9 Scenarios)

Runs all nine benchmark scenarios, exports CSV logs and comparison plots to `tests/test_results/`.

```bash
python tests/run_benchmarks.py
```

**Output:** For each scenario, the benchmark generates:
- `{scenario}_throughput.csv` — per-segment metrics for Throughput-based ABR
- `{scenario}_bola.csv` — per-segment metrics for BOLA
- `comparison_{scenario}.png` — side-by-side visualization (bitrate + buffer)

---

## 🖥️ Running the Streamlit Dashboard

Launch the interactive web application:

```bash
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

### Dashboard Features

1. **Upload custom data** — drag and drop your own `manifest.json` and `trace.txt` files.
2. **Configure parameters** — select ABR algorithm (BOLA / Throughput), adjust buffer capacity, toggle Hybrid Startup.
3. **Visualize results** — interactive Plotly chart showing bitrate selection and buffer level over time, with rebuffer event markers.
4. **QoE scorecard** — displays 5 metrics: QoE Score, Avg Bitrate, Total Rebuffer, Smoothness Penalty, Quality Switches.
5. **Detailed logs** — expandable table with per-segment simulation data.

---

## 📊 Input File Formats

### Manifest File (`.json`)

The server supports multiple JSON schemas:

```jsonc
// Schema 1: Standard format
{
    "Available_Bitrates": [500000, 1000000, 5000000],  // bps
    "Chunk_Count": 30,
    "Chunk_Time": 2,                                    // seconds
    "Chunks": {                                         // optional pre-computed sizes (bytes)
        "0": [125000, 250000, 1250000],
        "1": [123000, 248000, 1240000]
    }
}

// Schema 2: Alternative format (auto-converts kbps → bps)
{
    "bitrates_kbps": [300, 750, 1200, 4300, 6000],
    "segment_duration_s": 2.0,
    "total_segments": 30
}
```

If `Chunks` is not provided, the server generates VBR segment sizes using a truncated normal distribution.

### Network Trace File (`.txt`)

Two formats are supported:

```
# 2-column format: [timestamp_seconds] [bandwidth_bps]
0 500000
10 800000
20 1200000

# 1-column format: [bandwidth_bps] (timestamps auto-generated at 1s intervals)
4000000
500000
4000000
```

---

## 📐 QoE Metric Formula

The Quality of Experience score is computed as:

```
Ψ = Σ(Rk / 10⁶) - μ · Σ|ΔRk / 10⁶| - λ · Σ(Tk_rebuf)
```

| Symbol | Description | Default |
|:---|:---|:---|
| `Rk` | Selected bitrate for segment k (bps) | — |
| `ΔRk` | Bitrate change between consecutive segments | — |
| `Tk_rebuf` | Rebuffering duration for segment k (seconds) | — |
| `μ` | Smoothness penalty weight | 1.0 |
| `λ` | Rebuffering penalty weight | 4.3 |

---

## 📝 License

This project is developed for academic research purposes.
