import math
from abc import ABC, abstractmethod

class BaseABR(ABC):
    """
    Abstract Base Class for Adaptive Bitrate (ABR) algorithms.
    Acts as the standard interface for the decision core.
    """
    def __init__(self, bitrates: list[int]):
        # Ensure bitrates are sorted in ascending order for index consistency
        self.bitrates = sorted(bitrates)

    @abstractmethod
    def select_bitrate(self, current_buffer: float, network_history: list[float], chunk_sizes: list[int]) -> int:
        """
        Select the optimal bitrate index for the next video segment.

        Parameters:
            current_buffer (float): Current playback buffer occupancy in seconds.
            network_history (list[float]): Historical throughput logs (bps).
            chunk_sizes (list[int]): Segment sizes (in bytes) for each bitrate level.

        Returns:
            int: Selected bitrate index.
        """
        pass


class ThroughputABR(BaseABR):
    """
    Throughput-based ABR algorithm utilizing Harmonic Mean for bandwidth estimation.
    """
    def __init__(self, bitrates: list[int], window_size: int = 5, safety_margin: float = 0.9):
        super().__init__(bitrates)
        self.window_size = window_size
        self.safety_margin = safety_margin

    def _calculate_harmonic_mean(self, network_history: list[float]) -> float:
        if not network_history:
            return 0.0

        window = network_history[-self.window_size:]
        # Clamp minimum throughput to 1.0 bps to prevent division by zero
        sum_inverse = sum(1.0 / max(throughput, 1.0) for throughput in window)
        
        return len(window) / sum_inverse

    def select_bitrate(self, current_buffer: float, network_history: list[float], chunk_sizes: list[int]) -> int:
        # Fallback to base quality during startup
        if not network_history:
            return 0

        estimated_throughput = self._calculate_harmonic_mean(network_history)
        safe_throughput = estimated_throughput * self.safety_margin

        # Iterate backwards to find the maximum sustainable bitrate
        for i in range(len(self.bitrates) - 1, -1, -1):
            if self.bitrates[i] <= safe_throughput:
                return i

        return 0


class BolaABR(BaseABR):
    """
    Buffer Occupancy based Lyapunov Algorithm (BOLA).
    Maximizes utility while minimizing the risk of buffer starvation.
    """
    def __init__(self, bitrates: list[int], chunk_duration: float, max_buffer_size: float = 22.0):
        super().__init__(bitrates)
        self.chunk_duration = chunk_duration
        self.max_buffer_size = max_buffer_size
        
        # Minimum safe buffer threshold (Reservoir)
        self.tau = max(chunk_duration, chunk_duration * 1.3)
        
        # Pre-compute Utilities: v_m = ln(R_m / R_min)
        self.utilities = [math.log(max(r, 1) / max(self.bitrates[0], 1)) for r in self.bitrates]
        
        # Calculate Lyapunov control parameters
        u_max = self.utilities[-1]
        u_min = self.utilities[0]
        
        self.gamma_p = 0.5 * (u_max - u_min) 
        
        if (u_max + self.gamma_p) > 0:
            self.V = (self.max_buffer_size - self.tau) / (u_max + self.gamma_p)
        else:
            self.V = 3.0 
            
        # Tối ưu hóa: Tiền tính toán hằng số cho hàm mục tiêu
        self.precomputed_v_gamma = [self.V * (v_m + self.gamma_p) for v_m in self.utilities]

    def _safety_check(self, selected_index: int, current_buffer: float) -> int:
        if current_buffer < self.tau * 1.5 and selected_index == len(self.bitrates) - 1:
            return max(0, selected_index - 1)
            
        # Đã loại bỏ if dư thừa bên trong
        elif current_buffer < self.tau * 2.0 and selected_index == len(self.bitrates) - 1:
            return max(0, selected_index - 1)
                 
        return selected_index

    def select_bitrate(self, current_buffer: float, network_history: list[float], chunk_sizes: list[int]) -> int:
        # Fallback to lowest quality if buffer is critically low
        if current_buffer <= self.tau:
            return 0
            
        max_objective = float('-inf')
        best_index = 0
        
        # Objective Function maximization
        for m in range(len(self.bitrates)):
            S_m = max(chunk_sizes[m], 1) 
            Q_eff = current_buffer - self.tau
            
            # Tối ưu hóa: Sử dụng mảng đã tiền tính toán
            objective_val = (self.precomputed_v_gamma[m] - Q_eff) / S_m
            
            if objective_val > max_objective:
                max_objective = objective_val
                best_index = m
                
        return self._safety_check(best_index, current_buffer)