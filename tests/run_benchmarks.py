import os
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
import math

# Configure path to allow importing modules from the root 'core' directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(parent_dir)

from core.server import VirtualServer
from core.network import NetworkEnvironment
from core.abr_algorithms import ThroughputABR, BolaABR
from core.sim_engine import SimulationEngine
from core.metrics import QoECalculator

# Define static directories for automated testing
CONFIG_DIR = "tests/scenario_configs"
RESULTS_DIR = "tests/test_results"

def create_dummy_scenarios_if_missing():
    """
    Automatically generates a dummy test scenario if the configuration directory is empty.
    Ensures system robustness and prevents FileNotFoundError during initial setup.
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    if not os.listdir(CONFIG_DIR):
        print("⚠️ Configuration directory is empty. Generating 'test_dummy_3g' scenario...")
        dummy_dir = os.path.join(CONFIG_DIR, "test_dummy_3g")
        os.makedirs(dummy_dir, exist_ok=True)
        
        # Generate a sample manifest.json (Server Metadata)
        manifest_data = {
            "Available_Bitrates": [300000, 700000, 1500000, 3000000],
            "Chunk_Duration": 3.0,
            "Chunk_Count": 50
        }
        with open(os.path.join(dummy_dir, "manifest.json"), "w") as f:
            json.dump(manifest_data, f, indent=4)
            
        # Generate a sample trace.txt (Fluctuating Network Bandwidth)
        with open(os.path.join(dummy_dir, "trace.txt"), "w") as f:
            f.write("0.0 1000000\n10.0 500000\n20.0 1500000\n30.0 800000\n")
        print("✅ Dummy scenario created successfully.\n")

def run_simulation(server: VirtualServer, network: NetworkEnvironment, algo_instance, total_segments: int) -> list:
    """
    Executes the discrete-event simulation loop for a specific ABR algorithm.
    """
    engine = SimulationEngine(server=server, network=network, abr_algorithm=algo_instance)
    
    for k in range(total_segments):
        # Dynamically call the execution step based on the engine's interface
        if hasattr(engine, 'process_segment'):
            engine.process_segment(k)
        elif hasattr(engine, 'run_step'):
            engine.run_step(k)
        else:
            raise NotImplementedError("Could not find the simulation step method in SimulationEngine.")
            
    return engine.logs

def plot_and_save_comparison(logs_tp: list, logs_bola: list, scenario_name: str):
    """
    Visualizes and exports the performance comparison between Throughput and BOLA.
    Generates a 2x2 grid to separate the algorithms for clear visibility.
    """
    df_tp = pd.DataFrame(logs_tp)
    df_bola = pd.DataFrame(logs_bola)
    
    # Tạo lưới 2 hàng x 2 cột (Trái: TP, Phải: BOLA)
    fig, axes = plt.subplots(2, 2, figsize=(16, 8), sharex=True, sharey='row')
    fig.suptitle(f"ABR Performance Comparison: {scenario_name}", fontsize=16, fontweight='bold', y=0.95)
    
    # --- CỘT TRÁI: THROUGHPUT-BASED ---
    # 1. Bitrate của TP
    axes[0, 0].set_title("Throughput-based: Selected Bitrate", fontsize=12)
    axes[0, 0].step(df_tp['segment_index'], df_tp['bitrate_bps'] / 1e6, color='tab:blue', where='post')
    axes[0, 0].set_ylabel("Bitrate (Mbps)")
    axes[0, 0].grid(True, linestyle='--', alpha=0.6)
    
    # 2. Buffer của TP
    axes[1, 0].set_title("Throughput-based: Buffer Occupancy", fontsize=12)
    axes[1, 0].plot(df_tp['segment_index'], df_tp['buffer_level'], color='tab:blue')
    axes[1, 0].axhline(y=0, color='black', linestyle='-', linewidth=1.5) # Đường Stalling
    axes[1, 0].set_xlabel("Segment Index")
    axes[1, 0].set_ylabel("Buffer (s)")
    axes[1, 0].grid(True, linestyle='--', alpha=0.6)
    
    # --- CỘT PHẢI: BOLA ---
    # 3. Bitrate của BOLA
    axes[0, 1].set_title("BOLA: Selected Bitrate", fontsize=12)
    axes[0, 1].step(df_bola['segment_index'], df_bola['bitrate_bps'] / 1e6, color='tab:red', where='post')
    axes[0, 1].grid(True, linestyle='--', alpha=0.6)
    
    # 4. Buffer của BOLA
    axes[1, 1].set_title("BOLA: Buffer Occupancy", fontsize=12)
    axes[1, 1].plot(df_bola['segment_index'], df_bola['buffer_level'], color='tab:red')
    axes[1, 1].axhline(y=0, color='black', linestyle='-', linewidth=1.5) # Đường Stalling
    axes[1, 1].set_xlabel("Segment Index")
    axes[1, 1].grid(True, linestyle='--', alpha=0.6)
    
    plt.tight_layout(rect=[0, 0, 1, 0.93]) # Chừa chỗ cho suptitle
    
    # Tạo thư mục nếu chưa có
    os.makedirs(RESULTS_DIR, exist_ok=True)
    output_path = os.path.join(RESULTS_DIR, f"comparison_{scenario_name}.png")
    plt.savefig(output_path, dpi=300)
    plt.close()

def main():
    # 1. Initialize environment
    create_dummy_scenarios_if_missing()
    qoe_calculator = QoECalculator()
    
    # 2. Scan for available test scenarios
    scenarios = [d for d in os.listdir(CONFIG_DIR) if os.path.isdir(os.path.join(CONFIG_DIR, d))]
    
    for scenario in scenarios:
        print(f"🚀 Running benchmark for scenario: [{scenario}]")
        try:
            scenario_path = os.path.join(CONFIG_DIR, scenario)
            manifest_path = os.path.join(scenario_path, "manifest.json")
            trace_path = os.path.join(scenario_path, "trace.txt")
            
            # 3. Inject configuration data into system components
            server = VirtualServer(manifest_path=manifest_path)
            total_segments = server.total_segments
            
            # --- PHASE 1: Throughput-based Evaluation ---
            print("   -> Pass 1/2: Evaluating Throughput-based ABR...")
            network_tp = NetworkEnvironment(trace_path=trace_path)
            algo_tp = ThroughputABR(bitrates=server.bitrates)
            logs_tp = run_simulation(server, network_tp, algo_tp, total_segments)
            score_tp = qoe_calculator.calculate_qoe(logs_tp)
            
            # --- PHASE 2: BOLA Evaluation ---
            print("   -> Pass 2/2: Evaluating BOLA...")
            network_bola = NetworkEnvironment(trace_path=trace_path)
            
            # FIX: BolaABR requires both bitrates and chunk_duration according to abr_algorithms.py
            algo_bola = BolaABR(
                bitrates=server.bitrates,
                chunk_duration=server.segment_duration
            )
            logs_bola = run_simulation(server, network_bola, algo_bola, total_segments)
            score_bola = qoe_calculator.calculate_qoe(logs_bola)
            
            # --- PHASE 3: Data Export and Reporting ---
            print("   -> Exporting quantitative reports...")
            
            # Save logs as CSV
            pd.DataFrame(logs_tp).to_csv(os.path.join(RESULTS_DIR, f"{scenario}_throughput.csv"), index=False)
            pd.DataFrame(logs_bola).to_csv(os.path.join(RESULTS_DIR, f"{scenario}_bola.csv"), index=False)
            
            # Generate Visualization
            plot_and_save_comparison(logs_tp, logs_bola, scenario)
            
            # Print concise scorecard
            print(f"   📊 QoE Score -> Throughput: {score_tp['qoe_score']} | BOLA: {score_bola['qoe_score']}")
            print(f"   ⏳ Rebuffering -> Throughput: {score_tp['total_rebuffer_sec']}s | BOLA: {score_bola['total_rebuffer_sec']}s")
        except Exception as e:
            print(f"   ❌ ERROR: Scenario [{scenario}] failed: {e}")
        print("-" * 60)
        
    print("\n✅ All benchmarks completed successfully. Check the 'tests/test_results' folder for CSV logs and Graphs.")

if __name__ == "__main__":
    main()