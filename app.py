import streamlit as st
import tempfile
import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from core.server import VirtualServer
from core.network import NetworkEnvironment
from core.abr_algorithms import BolaABR, ThroughputABR
from core.sim_engine import SimulationEngine

def save_temp_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{uploaded_file.name}") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name

def main():
    st.set_page_config(page_title="ABR Streaming Simulator", page_icon="🎬", layout="wide")
    st.title("Adaptive Bitrate (ABR) Algorithm Simulator")

    # Quản lý State để không bị mất dữ liệu khi chuyển Tab hoặc kéo Slider
    if "sim_logs" not in st.session_state:
        st.session_state.sim_logs = None
    if "sim_qoe" not in st.session_state:
        st.session_state.sim_qoe = None

    st.sidebar.header("⚙️ Simulation Settings")
    
    manifest_file = st.sidebar.file_uploader("Upload Manifest (.json)", type=["json"])
    trace_file = st.sidebar.file_uploader("Upload Network Trace (.txt)", type=["txt"])
    
    abr_choice = st.sidebar.selectbox("Select ABR Algorithm", ["BOLA", "Throughput-based"])
    buffer_capacity = st.sidebar.slider("Max Buffer Capacity (sec)", min_value=10.0, max_value=60.0, value=22.0)
    use_hybrid = st.sidebar.checkbox("Enable Hybrid Fast-Startup", value=True)

    run_sim_btn = st.sidebar.button("🚀 Run Simulation")

    tab1, tab2 = st.tabs(["📊 Core Simulator Dashboard", "🎬 Interactive Playback"])

    with tab1:
        st.subheader("Simulation Results & QoE Evaluation")
        
        # Xử lý Logic khi bấm nút chạy
        if run_sim_btn:
            if manifest_file and trace_file:
                manifest_path = None
                trace_path = None
                
                with st.spinner("Running Discrete-Event Simulation..."):
                    try:
                        manifest_path = save_temp_file(manifest_file)
                        trace_path = save_temp_file(trace_file)
                        
                        server = VirtualServer(manifest_path)
                        network = NetworkEnvironment(trace_path)
                        
                        if abr_choice == "BOLA":
                            abr_algorithm = BolaABR(
                                bitrates=server.bitrates,
                                chunk_duration=server.segment_duration,
                                max_buffer_size=buffer_capacity
                            )
                        else:
                            abr_algorithm = ThroughputABR(bitrates=server.bitrates)
                            
                        engine = SimulationEngine(
                            server, network, abr_algorithm,
                            max_buffer_capacity=buffer_capacity,
                            use_hybrid_startup=use_hybrid
                        )
                        logs, final_qoe = engine.run_simulation()
                        
                        # Lưu kết quả vào session_state
                        st.session_state.sim_logs = logs
                        st.session_state.sim_qoe = final_qoe
                            
                    except Exception as e:
                        st.error(f"An error occurred during simulation: {e}")
                        
                    finally:
                        # Xóa file tạm an toàn (kiểm tra biến đã được gán và file tồn tại)
                        if manifest_path and os.path.exists(manifest_path):
                            os.remove(manifest_path)
                        if trace_path and os.path.exists(trace_path):
                            os.remove(trace_path)
            else:
                st.warning("⚠️ Please upload both Manifest and Trace files to run the simulation.")

        # Hiển thị kết quả từ session_state (Giúp UI tồn tại vĩnh viễn sau khi chạy)
        if st.session_state.sim_logs and st.session_state.sim_qoe:
            qoe_data = st.session_state.sim_qoe
            
            # Hiển thị bảng điểm QoE chi tiết
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("🏆 QoE Score", round(qoe_data.get("qoe_score", 0.0), 2))
            col2.metric("📶 Avg Bitrate (Mbps)", round(qoe_data.get("average_bitrate_mbps", 0.0), 3))
            col3.metric("⏸️ Total Rebuffer (s)", round(qoe_data.get("total_rebuffer_sec", 0.0), 3))
            col4.metric("📉 Smoothness Penalty", round(qoe_data.get("total_smoothness_penalty", 0.0), 3))
            col5.metric("🔄 Quality Switches", qoe_data.get("quality_switches_count", 0))
            
            df = pd.DataFrame(st.session_state.sim_logs)
            
            # Đồ thị chính: Bitrate vs Buffer Level
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            
            # FIX: go.Step không tồn tại trong Plotly → dùng go.Scatter với line_shape='hv' (step chart)
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'], y=df['bitrate_bps'] / 1e6,
                    name="Bitrate (Mbps)", mode='lines',
                    line=dict(color='#636EFA', shape='hv', width=2)
                ),
                secondary_y=False
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'], y=df['buffer_level'],
                    name="Buffer Level (sec)", mode='lines',
                    line=dict(color='#EF553B', shape='spline', width=2),
                    fill='tozeroy', fillcolor='rgba(239, 85, 59, 0.1)'
                ),
                secondary_y=True
            )
            
            # Đánh dấu các sự kiện rebuffering trên đồ thị
            rebuffer_events = df[df['rebuffer_time'] > 0]
            if not rebuffer_events.empty:
                fig.add_trace(
                    go.Scatter(
                        x=rebuffer_events['timestamp'], y=rebuffer_events['buffer_level'],
                        name="⚠️ Rebuffer Event", mode='markers',
                        marker=dict(color='red', size=10, symbol='x')
                    ),
                    secondary_y=True
                )
            
            fig.update_layout(
                title_text="Buffer Level vs. Bitrate Selection Over Time",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_xaxes(title_text="Playback Time (s)")
            fig.update_yaxes(title_text="Bitrate (Mbps)", secondary_y=False)
            fig.update_yaxes(title_text="Buffer Level (s)", secondary_y=True)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Bảng log chi tiết từng segment (có thể mở rộng)
            with st.expander("📋 View Detailed Segment Logs"):
                st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Visual Impact of Bitrate Compression")
        st.write("Adjust the simulated network bandwidth to observe dynamic video quality adaptation.")
        
        simulated_bandwidth = st.slider("Current Network Bandwidth (kbps)", min_value=200, max_value=5000, value=1500, step=100)
        
        st.markdown("### Live Playback Simulation")
        
        if simulated_bandwidth < 1000:
            st.info("Status: Low Bandwidth. Displaying Low Quality (360p).")
        elif simulated_bandwidth < 3000:
            st.info("Status: Medium Bandwidth. Displaying Standard Quality (720p).")
        else:
            st.success("Status: High Bandwidth. Displaying High Definition (1080p).")

if __name__ == "__main__":
    main()