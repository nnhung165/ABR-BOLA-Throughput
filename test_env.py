import os
from core.server import VirtualServer
from core.network import NetworkEnvironment

def test_server():
    print("--------------------------------------------------")
    print("[1] TESTING ZONE 1: VIRTUAL SERVER")
    print("--------------------------------------------------")
    
    # Define file path
    manifest_file = "dataset/manifest.json"
    
    # Initialize the server
    server = VirtualServer(manifest_file)
    
    print(f"Total segments: {server.total_segments}")
    print(f"Available bitrates: {server.bitrates}")
    
    # Test getting segment sizes for segment 0 at all bitrates
    print("\nSegment Sizes for k = 0 (in bits):")
    for m in range(len(server.bitrates)):
        size = server.get_segment_size(k=0, m=m)
        print(f"  - Bitrate index {m}: {size:.2f} bits")

def test_network():
    print("\n--------------------------------------------------")
    print("[2] TESTING ZONE 2: NETWORK ENVIRONMENT")
    print("--------------------------------------------------")
    
    # Define file path
    trace_file = "dataset/trace.txt"
    
    # Initialize the network with custom RTT and Jitter
    network = NetworkEnvironment(trace_file, base_rtt=0.05, jitter_factor=0.05)
    
    print(f"Max trace duration: {network.max_trace_time} seconds")
    
    # Test looping behavior (e.g., checking at 1.5s, 3.5s, and 5.5s which should loop back)
    test_times = [1.5, 3.5, 5.5]
    
    print("\nNetwork Conditions at specific times:")
    for t in test_times:
        net_cond = network.get_network_conditions(current_time=t)
        bw = net_cond["bandwidth_bps"]
        rtt = net_cond["rtt_seconds"]
        print(f"  - Time {t}s -> Bandwidth: {bw:.2f} bps | RTT: {rtt}s")

if __name__ == "__main__":
    # Check if files exist before testing
    if not os.path.exists("dataset/manifest.json") or not os.path.exists("dataset/trace.txt"):
        print("Error: Missing mock data files. Please create them in the 'dataset' folder.")
    else:
        test_server()
        test_network()