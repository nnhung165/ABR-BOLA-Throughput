class SimBuffer:
    """
    Simulates the video playback buffer dynamics in a discrete-event environment.
    Tracks buffer occupancy (Q(t)) and calculates rebuffering (stalling) events.
    """
    def __init__(self, max_capacity: float = 22.0):
        """
        Initialize an empty playback buffer.
        
        Parameters:
            max_capacity (float): Maximum buffer size in seconds.
        """
        self.level = 0.0
        self.max_capacity = max_capacity
        self.total_rebuffering_time = 0.0

    def simulate_download(self, download_time: float, chunk_duration: float) -> float:
        """
        Update the buffer state after attempting to download a video segment.
        This function simulates the simultaneous draining (playback) and filling (downloading)
        of the video buffer.
        
        Parameters:
            download_time (float): Time elapsed to download the chunk (T_k).
            chunk_duration (float): Media playback duration of the chunk (p).
            
        Returns:
            float: Rebuffering duration (in seconds) caused by this download event.
        """
        rebuffering_time = 0.0
        
        # Step 1: Buffer Depletion Phase (Playback during download)
        # If it takes longer to download than what we have in the buffer, the video freezes.
        if download_time > self.level:
            rebuffering_time = download_time - self.level
            self.level = 0.0  # Buffer is completely starved
        else:
            self.level -= download_time  # Normal playback drains the buffer

        # Step 2: Buffer Refill Phase
        # The new chunk is successfully downloaded and added to the queue
        self.level += chunk_duration
        
        # Prevent buffer overflow (Buffer constraint)
        self.level = min(self.level, self.max_capacity)

        # Step 3: Accumulate total stalling metrics for QoE evaluation
        self.total_rebuffering_time += rebuffering_time

        return rebuffering_time
        
    def get_level(self) -> float:
        """
        Retrieve the current buffer occupancy Q(t).
        """
        return self.level
        
    def reset(self):
        """
        Reset the buffer state for a new simulation session.
        """
        self.level = 0.0
        self.total_rebuffering_time = 0.0