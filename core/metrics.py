from typing import List, Dict, Any

class QoECalculator:
    """
    Quality of Experience (QoE) evaluator based on standard ABR objective metrics.
    Quantifies user satisfaction by rewarding high bitrates and penalizing
    stalls (rebuffering) and quality fluctuations (smoothness penalty).
    """
    def __init__(self, rebuffer_penalty: float = 4.3, smoothness_penalty: float = 1.0):
        self.rebuffer_penalty = rebuffer_penalty
        self.smoothness_penalty = smoothness_penalty

    def calculate_qoe(self, logs: List[Dict[str, Any]]) -> Dict[str, float]:
        if not logs:
            return {
                "qoe_score": 0.0, 
                "average_bitrate_mbps": 0.0, 
                "total_rebuffer_sec": 0.0, 
                "total_smoothness_penalty": 0.0,
                "quality_switches_count": 0
            }

        total_utility = 0.0
        total_smoothness_penalty = 0.0
        total_rebuffer_time = 0.0
        
        # Biến phụ trợ cho tối ưu vòng lặp
        total_bitrate_bps = 0
        quality_switches = 0
        total_logs = len(logs)

        for i, log in enumerate(logs):
            current_bps = log["bitrate_bps"]
            current_bitrate_mbps = current_bps / 1000000.0
            
            # Tích lũy giá trị trực tiếp
            total_utility += current_bitrate_mbps
            total_rebuffer_time += log["rebuffer_time"]
            total_bitrate_bps += current_bps

            if i > 0:
                prev_log = logs[i-1]
                prev_bitrate_mbps = prev_log["bitrate_bps"] / 1000000.0
                total_smoothness_penalty += abs(current_bitrate_mbps - prev_bitrate_mbps)
                
                # Đếm số lần chuyển đổi bitrate ngay trong vòng lặp chính
                if log["bitrate_index"] != prev_log["bitrate_index"]:
                    quality_switches += 1

        # Tính toán kết quả cuối cùng
        qoe_score = total_utility - (self.smoothness_penalty * total_smoothness_penalty) - (self.rebuffer_penalty * total_rebuffer_time)
        average_bitrate_bps = total_bitrate_bps / total_logs

        return {
            "qoe_score": round(qoe_score, 3),
            "average_bitrate_mbps": round(average_bitrate_bps / 1000000.0, 3),
            "total_rebuffer_sec": round(total_rebuffer_time, 3),
            "total_smoothness_penalty": round(total_smoothness_penalty, 3),
            "quality_switches_count": quality_switches
        }