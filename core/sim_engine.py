from typing import List, Dict, Any, Tuple
from core.abr_algorithms import BaseABR, ThroughputABR
from core.buffer import SimBuffer
from core.metrics import QoECalculator

class SimulationEngine:
    """
    The core event loop tying together the Server, Network, and ABR Logic.
    Executes the discrete-event simulation for the video streaming session.
    """
    def __init__(self, server: Any, network: Any, abr_algorithm: BaseABR, 
                 max_buffer_capacity: float = 22.0, 
                 use_hybrid_startup: bool = True):
        self.server = server
        self.network = network
        self.abr = abr_algorithm
        
        # Initialize playback buffer
        self.buffer = SimBuffer(max_capacity=max_buffer_capacity)
        
        self.current_time = 0.0
        self.network_history: List[float] = []
        self.logs: List[Dict[str, Any]] = []
        
        # Hybrid startup (Use Throughput to build buffer quickly before BOLA takes over)
        self.use_hybrid_startup = use_hybrid_startup
        if self.use_hybrid_startup:
            # Validate server attributes to avoid runtime crashes
            if not hasattr(self.server, 'bitrates') or not hasattr(self.server, 'segment_duration'):
                raise AttributeError("Server object missing required attributes: 'bitrates' or 'segment_duration'")
                
            self.startup_abr = ThroughputABR(bitrates=self.server.bitrates, window_size=5, safety_margin=0.9)

    def process_segment(self, k: int):
        """
        Executes a single simulation step for segment index 'k'.
        This method is dynamically called by run_benchmarks.py
        """
        # Fetch chunk sizes in Bytes for all bitrates at index k
        chunk_sizes_bytes = [self.server.get_segment_size(k, m) for m in range(len(self.server.bitrates))]
        
        # [BOLA GUARD]: Phát hiện dữ liệu Server bị lỗi/rỗng
        # Ngưỡng động: 5% kích thước kỳ vọng của bitrate thấp nhất (tránh cảnh báo giả trên stream bitrate thấp)
        min_expected_size = (min(self.server.bitrates) * self.server.segment_duration) / 8.0
        guard_threshold = max(min_expected_size * 0.05, 100.0)  # Sàn tối thiểu 100 bytes
        if any(size < guard_threshold for size in chunk_sizes_bytes):
            print(f"⚠️ CẢNH BÁO: Kích thước phân đoạn {k} quá nhỏ (Dưới {guard_threshold:.0f}B). Vui lòng kiểm tra hàm get_segment_size() trong server.py!")

        # Choose the ABR algorithm (Hybrid Startup Logic)
        if self.use_hybrid_startup and self.buffer.level < self.server.segment_duration * 3:
            # Buffer is low, use throughput to aggressively build buffer
            selected_index = self.startup_abr.select_bitrate(
                current_buffer=self.buffer.level,
                network_history=self.network_history,
                chunk_sizes=chunk_sizes_bytes
            )
        else:
            # Steady state, use the primary algorithm (e.g., BOLA)
            selected_index = self.abr.select_bitrate(
                current_buffer=self.buffer.level,
                network_history=self.network_history,
                chunk_sizes=chunk_sizes_bytes
            )
            
        selected_size_bytes = chunk_sizes_bytes[selected_index]
        selected_bitrate_bps = self.server.bitrates[selected_index]

        # Get network conditions at current simulation time
        net_conditions = self.network.get_network_conditions(self.current_time)
        current_bandwidth_bps = net_conditions["bandwidth_bps"]
        rtt_seconds = net_conditions.get("rtt_seconds", 0.05)
        
        # Calculate download time: T_k = RTT + (S_m / w(t))
        chunk_size_bits = selected_size_bytes * 8.0 
        download_time = rtt_seconds + (chunk_size_bits / max(current_bandwidth_bps, 1000.0))
        
        # Record perceived throughput for future decisions
        # (Chỉ đo lường throughput thuần túy, không tính RTT để phản ánh đúng tốc độ băng thông thực)
        actual_transmission_time = download_time - rtt_seconds
        measured_throughput = chunk_size_bits / actual_transmission_time if actual_transmission_time > 0 else current_bandwidth_bps
        self.network_history.append(measured_throughput)
        
        # Update Buffer and calculate rebuffering (Block 5)
        rebuffer_time = self.buffer.simulate_download(download_time, self.server.segment_duration)
        
        # QUAN TRỌNG: Advance simulation clock (Fix lỗi bẻ cong thời gian)
        self.current_time += download_time
        
        # Log metrics for Dashboard/Metrics component
        self.logs.append({
            "segment_index": k,
            "timestamp": round(self.current_time, 3),
            "bitrate_index": selected_index,
            "bitrate_bps": selected_bitrate_bps,
            "buffer_level": round(self.buffer.level, 3),
            "rebuffer_time": round(rebuffer_time, 3),
            "download_time": round(download_time, 3),
            "measured_bandwidth_bps": round(current_bandwidth_bps, 3)
        })

    def run_simulation(self) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
        """
        Execute the full discrete-event simulation across all video segments.
        
        Returns:
            Tuple containing:
                - logs (list[dict]): Per-segment metrics log.
                - qoe (dict): Final QoE evaluation scores.
        """
        # Reset state for a clean run
        self.buffer.reset()
        self.current_time = 0.0
        self.network_history = []
        self.logs = []
        
        for k in range(self.server.total_segments):
            self.process_segment(k)
            
        # Calculate final QoE score
        qoe_calculator = QoECalculator()
        qoe_results = qoe_calculator.calculate_qoe(self.logs)
        
        return self.logs, qoe_results