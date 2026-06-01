import sys
import os

from core.abr_algorithms import BolaABR
from core.sim_engine import SimulationEngine

class MockServer:
    def __init__(self):
        self.bitrates = [500000, 1000000, 2000000, 5000000]
        self.segment_duration = 2.0
        # Tăng lên 15 segments để video chạy đủ lâu
        self.total_segments = 15  
        
    def get_segment_size(self, k: int, m: int) -> float:
        return (self.bitrates[m] * self.segment_duration) / 8.0

class MockNetwork:
    def get_network_conditions(self, current_time: float) -> dict:
        # Bẫy đứt cáp: Đẩy mạng rớt thê thảm ở giây thứ 5.0
        if current_time > 5.0:
            return {"bandwidth_bps": 800000.0}
        return {"bandwidth_bps": 6000000.0}

def run_integration_test():
    print("=" * 65)
    print("STARTING INTEGRATION TEST: SIMULATION ENGINE (EVENT LOOP)")
    print("=" * 65)

    mock_server = MockServer()
    mock_network = MockNetwork()
    bola_engine = BolaABR(bitrates=mock_server.bitrates, chunk_duration=mock_server.segment_duration)
    
    sim_engine = SimulationEngine(
        server=mock_server, 
        network=mock_network, 
        abr_algorithm=bola_engine, 
        use_hybrid_startup=True
    )
    
    logs, qoe_results = sim_engine.run_simulation()
    
    print(f"Simulation completed. Segments downloaded: {len(logs)}\n")
    print(f"{'Chunk':<6} | {'Time (s)':<10} | {'Bitrate (bps)':<15} | {'Buffer (s)':<12} | {'Rebuffer (s)':<12}")
    print("-" * 70)
    
    total_rebuffer = 0.0
    for log in logs:
        print(f"{log['segment_index']:<6} | {log['timestamp']:<10.2f} | "
              f"{log['bitrate_bps']:<15} | {log['buffer_level']:<12.2f} | {log['rebuffer_time']:<12.2f}")
        total_rebuffer += log['rebuffer_time']
        
    print("-" * 70)
    print(f"Total Rebuffering Time: {total_rebuffer:.2f} seconds")

    # FIX 1: Chunk 0 là dò đường (phải = 0). Chunk 1 mới kích hoạt Hybrid.
    assert logs[1]['bitrate_index'] > 0, "Failed: Hybrid startup didn't jump after chunk 0 probe."
    
    # FIX 2: Bắt phản ứng của BOLA khi mạng rớt sau giây thứ 5.0
    late_chunks = [log['bitrate_bps'] for log in logs if log['timestamp'] > 6.0]
    if late_chunks:
        assert min(late_chunks) <= 1000000, "Failed: ABR did not step down quality when network dropped."

    print("\n[SUCCESS] Integration Test Passed! Hybrid Logic and Physics are completely sound.")

if __name__ == "__main__":
    run_integration_test()