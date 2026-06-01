import sys
import os

from core.abr_algorithms import ThroughputABR, BolaABR

def run_benchmarks():
    """
    Execute unit tests on ABR core decision logic using edge-case simulation states.
    """
    BITRATES = [500000, 1000000, 2000000, 5000000]
    MOCK_CHUNK_SIZES = [125000, 250000, 500000, 1250000]
    CHUNK_DURATION = 2.0
    
    throughput_engine = ThroughputABR(bitrates=BITRATES, window_size=5, safety_margin=0.9)
    bola_engine = BolaABR(bitrates=BITRATES, chunk_duration=CHUNK_DURATION, max_buffer_size=20.0)
    
    print("=" * 60)
    print("STARTING AUTONOMOUS UNIT TEST: ABR ALGORITHMIC CORE")
    print("=" * 60)

    print("\n[CASE 1] System Cold Startup Evaluation")
    print("State: Current Buffer = 0.0s, Network History = []")
    
    idx_t1 = throughput_engine.select_bitrate(0.0, [], MOCK_CHUNK_SIZES)
    idx_b1 = bola_engine.select_bitrate(0.0, [], MOCK_CHUNK_SIZES)
    
    print(f" -> ThroughputABR selected index: {idx_t1} (Expected: 0)")
    print(f" -> BolaABR       selected index: {idx_b1} (Expected: 0)")
    assert idx_t1 == 0 and idx_b1 == 0, "Startup validation failed."

    print("\n[CASE 2] Transient Network Spike vs Critically Low Buffer")
    print("State: Current Buffer = 1.5s, Network History = [6.0 Mbps, 6.0 Mbps]")
    mock_history_high = [6000000.0, 6000000.0]
    
    idx_t2 = throughput_engine.select_bitrate(1.5, mock_history_high, MOCK_CHUNK_SIZES)
    idx_b2 = bola_engine.select_bitrate(1.5, mock_history_high, MOCK_CHUNK_SIZES)
    
    print(f" -> ThroughputABR selected index: {idx_t2} (Aggressive optimization via speed)")
    print(f" -> BolaABR       selected index: {idx_b2} (Conservative fallback via Lyapunov)")
    assert idx_b2 < idx_t2, "Lyapunov protective mechanism failed to throttle bitrate index."

    print("\n[CASE 3] Ideal Steady State Convergence")
    print("State: Current Buffer = 15.0s, Network History = [6.0 Mbps, 6.0 Mbps]")
    
    idx_t3 = throughput_engine.select_bitrate(15.0, mock_history_high, MOCK_CHUNK_SIZES)
    idx_b3 = bola_engine.select_bitrate(15.0, mock_history_high, MOCK_CHUNK_SIZES)
    
    print(f" -> ThroughputABR selected index: {idx_t3} (Expected: 3)")
    print(f" -> BolaABR       selected index: {idx_b3} (Expected: 3)")
    assert idx_t3 == 3 and idx_b3 == 3, "Max-tier steady state convergence failed."

    print("\n" + "=" * 60)
    print("UNIT TEST RESULT: ALL ABR LOGIC VERIFICATIONS PASSED")
    print("=" * 60)

if __name__ == "__main__":
    run_benchmarks()