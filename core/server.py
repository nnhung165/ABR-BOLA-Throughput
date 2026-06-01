import json
import numpy as np
from typing import List

class VirtualServer:
    def __init__(self, manifest_path: str):
        """
        Initialize the Virtual Server, load the MPD manifest, and configure the video matrix.
        """
        self.manifest_path = manifest_path
        
        # Manifest Metadata
        self.bitrates: List[float] = []    # Video profiles (bps)
        self.segment_duration: float = 0.0 # Length of each segment (seconds)
        self.total_segments: int = 0       # Total chunk count
        
        # Extended Metadata for Edge-Case Testing
        self.target_buffer_size: float = 22.0  # Default 22 seconds
        self.preferred_bitrate: float = None   # Default None
        
        # Segment Matrix (N x M) containing sizes in BYTES
        self.segment_sizes_matrix: np.ndarray = None  
        
        self._load_manifest()

    def _load_manifest(self):
        """
        Load data from JSON. Supports both custom maps and pre-generated dataset matrices.
        """
        try:
            with open(self.manifest_path, 'r') as f:
                data = json.load(f)
                
            # Parse keys adapting to multiple dataset schemas
            raw_bitrates = data.get("Available_Bitrates", data.get("bitrates", []))
            
            # Support bitrates_kbps schema (convert kbps -> bps)
            if not raw_bitrates:
                raw_bitrates_kbps = data.get("bitrates_kbps", [])
                raw_bitrates = [b * 1000 for b in raw_bitrates_kbps]
                
            self.bitrates = [float(b) for b in raw_bitrates]
            
            # Số phân đoạn MÔ PHỎNG (Ví dụ: 30 chunks)
            self.total_segments = int(data.get("Chunk_Count", data.get("total_segments", 30)))
            self.segment_duration = float(data.get("Chunk_Time", data.get("segment_duration", data.get("segment_duration_s", 3.0))))
            
            if "Buffer_Size" in data:
                self.target_buffer_size = float(data["Buffer_Size"])
                
            pref_bitrate = data.get("Preferred_Bitrate")
            if pref_bitrate is not None:
                self.preferred_bitrate = float(pref_bitrate)
            
            if not self.bitrates or self.total_segments <= 0:
                raise ValueError("Invalid configuration: check bitrate array or segment limits.")
            
            # Look for pre-existing chunk sizes in the dataset
            chunks_data = data.get("Chunks")
            if chunks_data:
                # [BOLA FIX]: Tách biệt số lượng chunk THỰC TẾ có trong JSON để xoay vòng
                self.data_chunk_count = max([int(k) for k in chunks_data.keys()]) + 1
                
                # Khởi tạo ma trận bằng đúng số lượng data thực tế (Ví dụ: 5 hàng)
                self.segment_sizes_matrix = np.zeros((self.data_chunk_count, len(self.bitrates)))
                for chunk_id, size_list in chunks_data.items():
                    k = int(chunk_id)
                    if k < self.data_chunk_count:
                        self.segment_sizes_matrix[k, :] = [float(size) for size in size_list]
            else:
                # Fallback to random statistical model
                self.data_chunk_count = self.total_segments
                self._generate_vbr_matrix()
                
        except (FileNotFoundError, json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(f"Server init failed for {self.manifest_path}: {e}")

    def _generate_vbr_matrix(self):
        """
        Fallback VBR generator using Vectorized Truncated Normal Distribution.
        Re-rolls invalid entries below the floor value to preserve statistical shape.
        """
        N = self.total_segments
        M = len(self.bitrates)
        self.segment_sizes_matrix = np.zeros((N, M))
        
        for m_idx, bitrate in enumerate(self.bitrates):
            # Convert bits to Bytes (bitrate * duration / 8.0) to align with dataset format
            mean_size = (bitrate * self.segment_duration) / 8.0 
            std_dev = mean_size * 0.20
            
            raw_sizes = np.random.normal(loc=mean_size, scale=std_dev, size=N)
            floor_value = mean_size * 0.10
            
            invalid_mask = raw_sizes < floor_value
            while np.any(invalid_mask):
                num_invalid = np.sum(invalid_mask)
                raw_sizes[invalid_mask] = np.random.normal(loc=mean_size, scale=std_dev, size=num_invalid)
                invalid_mask = raw_sizes < floor_value
                
            self.segment_sizes_matrix[:, m_idx] = raw_sizes

    def get_segment_size(self, k: int, m: int) -> float:
        """
        API endpoint to request specific segment sizes.
        Optimized with Virtual Looping to resolve short emulation window limits.
        """
        if 0 <= m < len(self.bitrates):
            # Xoay vòng kịch bản liên tục dựa trên số lượng dữ liệu THỰC TẾ
            virtual_k = k % getattr(self, 'data_chunk_count', self.total_segments)
            size_bytes = self.segment_sizes_matrix[virtual_k, m]
            
            return max(float(size_bytes), 1000.0)
        else:
            raise IndexError(f"Bitrate index out of bounds: m={m}")