import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image
import streamlit.components.v1 as components

st.set_page_config(page_title="High-Res Narrator Studio", layout="wide")

# --- 1. THE JAVASCRIPT RECORDER (MIC + SCREEN MERGE) ---
record_js = """
<script>
let mediaRecorder;
let recordedChunks = [];

async function startRecording() {
    try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ 
            video: { cursor: "always" }, 
            audio: true 
        });
        const voiceStream = await navigator.mediaDevices.getUserMedia({ 
            audio: true, video: false 
        });
        const combinedStream = new MediaStream([
            ...screenStream.getVideoTracks(),
            ...voiceStream.getAudioTracks()
        ]);
        mediaRecorder = new MediaRecorder(combinedStream);
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: "video/webm" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "research_trailer.webm";
            a.click();
            recordedChunks = [];
            combinedStream.getTracks().forEach(t => t.stop());
        };
        mediaRecorder.start();
        alert("🎤 Recording! Present your slides now.");
    } catch (err) { alert("Access denied."); }
}
function stopRecording() { mediaRecorder.stop(); }
</script>
<div style="text-align: center;">
    <button onclick="startRecording()" style="background:#ff4b4b; color:white; border:none; padding:12px 24px; border-radius:5px; cursor:pointer; font-weight:bold;">🔴 START RECORDING</button>
    <button onclick="stopRecording()" style="background:#444; color:white; border:none; padding:12px 24px; border-radius:5px; cursor:pointer; margin-left:10px;">⏹️ STOP & DOWNLOAD</button>
</div>
"""

# --- 2. THE UI LAYOUT ---
st.title("🔬 High-Res Narrator Studio")

uploaded_pdf = st.file_uploader("Upload Paper (PDF)", type="pdf")

if uploaded_pdf:
    if 'slides' not in st.session_state:
        with st.spinner("Rendering High-Res Slides (4.0x DPI)..."):
            doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
            slides = []
            # 4.0 Zoom for crisp text/graphs
            mat = fitz.Matrix(4.0, 4.0) 
            for page in doc:
                pix = page.get_pixmap(matrix=mat)
                slides.append(Image.open(io.BytesIO(pix.tobytes())))
            st.session_state.slides = slides

    if 'slides' in st.session_state:
        st.divider()
        col_stage, col_tools = st.columns([3, 1])
        
        with col_tools:
            st.markdown("### 🛠️ Studio")
            components.html(record_js, height=100)
            
            st.divider()
            slide_idx = st.select_slider("Navigate Slides", options=range(len(st.session_state.slides)))
            
            # The "Overlay" Preview (Simulating the bubble)
            st.camera_input("Narrator Bubble Preview")
            st.info("Tip: Position your camera window so it doesn't cover your data!")

        with col_stage:
            # Display the high-res slide
            st.image(st.session_state.slides[slide_idx], use_container_width=True)