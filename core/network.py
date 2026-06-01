import numpy as np

class NetworkEnvironment:
    def __init__(self, trace_path: str, base_rtt: float = 0.05, jitter_factor: float = 0.05):
        """
        Initialize the Network Layer. Parses logs with layout: [timestamp] [bandwidth]
        """
        self.trace_path = trace_path
        self.base_rtt = base_rtt
        self.jitter_factor = jitter_factor
        
        self.time_stamps: np.ndarray = np.array([])
        self.bandwidths: np.ndarray = np.array([])
        self.max_trace_time: float = 0.0
        
        self._load_trace()

    def _load_trace(self):
        """
        Read the trace file and map the network profiles over time.
        Supports both 2-column format [timestamp bandwidth] and 
        single-column format [bandwidth] (auto-generates timestamps).
        """
        try:
            with open(self.trace_path, 'r') as f:
                lines = f.readlines()
            
            temp_times = []
            temp_bws = []
            single_column_bws = []
            
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                    
                if len(parts) >= 2:
                    # Standard 2-column format: [timestamp] [bandwidth]
                    try:
                        t_val = float(parts[0])
                        bw_val = float(parts[1])
                        temp_times.append(t_val)
                        temp_bws.append(bw_val)
                    except ValueError:
                        continue
                elif len(parts) == 1:
                    # Single-column format: [bandwidth] only
                    try:
                        bw_val = float(parts[0])
                        single_column_bws.append(bw_val)
                    except ValueError:
                        continue
            
            # If no 2-column data found, use single-column with auto-generated timestamps
            if not temp_bws and single_column_bws:
                default_interval = 1.0  # 1 second per entry
                temp_bws = single_column_bws
                temp_times = [i * default_interval for i in range(len(single_column_bws))]
            
            if not temp_bws:
                raise ValueError("No valid network profiles found inside the log file.")
                
            self.time_stamps = np.array(temp_times)
            self.bandwidths = np.array(temp_bws)
            
            # Use the final explicit timestamp value as our track length limit
            self.max_trace_time = float(self.time_stamps[-1])
            
        except (FileNotFoundError, ValueError) as e:
            raise RuntimeError(f"Network environment initialization failed: {e}")

    def get_network_conditions(self, current_time: float) -> dict:
        """
        Retrieve network status indicators using linear interpolation and stochastic TCP flow noise.
        Resolves coarse granularity issues by smoothing transitions between data nodes.
        """
        if self.max_trace_time <= 0:
            # Fallback for flat network traces (e.g., traceALT2.txt)
            base_bw = float(self.bandwidths[0]) if self.bandwidths.size > 0 else 0.0
        else:
            # Wrap timeline using modulo operator to sustain continuous simulation loops
            looped_time = current_time % self.max_trace_time
            
            # Perform linear interpolation to generate clean curves instead of static steps
            base_bw = float(np.interp(looped_time, self.time_stamps, self.bandwidths))
            
        # Add a stochastic variance noise to mimic real-world TCP congestion window shifts
        noise = np.random.uniform(-self.jitter_factor, self.jitter_factor)
        noisy_bw = base_bw * (1.0 + noise)
        
        return {
            "bandwidth_bps": max(1000.0, noisy_bw), # Safeguard floor value to prevent ZeroDivisionError
            "rtt_seconds": self.base_rtt
        }