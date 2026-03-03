import streamlit as st
import os
import fitz  # PyMuPDF
import io
import requests
import base64
from PIL import Image
import streamlit.components.v1 as components

# --- 1. CONFIG & STORAGE ---
st.set_page_config(page_title="ScholarTube", layout="wide", page_icon="🔬")

if not os.path.exists("uploads"):
    os.makedirs("uploads")

# --- 2. METADATA ENGINE (CrossRef API) ---
def get_paper_metadata(doi):
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()['message']
            title = data.get('title', ['Unknown Title'])[0]
            journal = data.get('container-title', [''])[0]
            return {
                "title": title,
                "journal": journal
            }
    except:
        return None
    return None

# --- 3. GLOBAL RECORDER + MIC SELECTOR + PIP BUBBLE ---
record_js = """
<script>
let mediaRecorder;
let recordedChunks = [];
let pipVideo;

// Function to populate the microphone list
async function getMicrophones() {
    try {
        const devices = await navigator.mediaDevices.enumerateDevices();
        const audioDevices = devices.filter(device => device.kind === 'audioinput');
        const select = document.getElementById('micSelect');
        select.innerHTML = '';
        audioDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.deviceId;
            option.text = device.label || `Microphone ${select.length + 1}`;
            select.appendChild(option);
        });
    } catch (err) { console.error("Error listing mics:", err); }
}

async function startBubble() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        pipVideo = document.createElement('video');
        pipVideo.srcObject = stream;
        pipVideo.muted = true;
        pipVideo.play();
        
        pipVideo.addEventListener('loadedmetadata', () => {
            pipVideo.requestPictureInPicture();
        });
    } catch (err) { alert("Camera access denied."); }
}

async function startRecording() {
    try {
        const micId = document.getElementById('micSelect').value;
        
        // Capture Screen (PowerPoint/Desktop)
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ 
            video: { cursor: "always" }, 
            audio: true 
        });
        
        // Capture selected Microphone
        const voiceStream = await navigator.mediaDevices.getUserMedia({ 
            audio: { deviceId: micId ? { exact: micId } : undefined } 
        });
        
        const combined = new MediaStream([
            ...screenStream.getVideoTracks(), 
            ...voiceStream.getAudioTracks()
        ]);

        mediaRecorder = new MediaRecorder(combined);
        mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) recordedChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            const blob = new Blob(recordedChunks, { type: "video/webm" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "jclub_trailer.webm";
            a.click();
            recordedChunks = [];
            combined.getTracks().forEach(t => t.stop());
        };
        mediaRecorder.start();
    } catch (err) { alert("Recording access denied."); }
}

function stopAll() {
    if(mediaRecorder) mediaRecorder.stop();
    if(document.pictureInPictureElement) document.exitPictureInPicture();
}

// Initial permission request to label microphones
navigator.mediaDevices.getUserMedia({ audio: true }).then(getMicrophones);
</script>
<div style="background: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333; color: white; font-family: sans-serif;">
    <label style="font-size: 12px; margin-bottom: 5px; display: block;">🎙️ Select Microphone:</label>
    <select id="micSelect" style="width: 100%; background: #333; color: white; border: 1px solid #555; padding: 8px; border-radius: 4px; margin-bottom: 15px;"></select>
    
    <button onclick="startBubble()" style="background:#4b4bff; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer; font-weight:bold; margin-bottom:10px; width:100%;">🔵 1. POP OUT BUBBLE</button>
    <div style="display: flex; gap: 5%;">
        <button onclick="startRecording()" style="background:#ff4b4b; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer; font-weight:bold; width:45%;">🔴 2. RECORD</button>
        <button onclick="stopAll()" style="background:#444; color:white; border:none; padding:10px; border-radius:5px; cursor:pointer; width:45%;">⏹️ STOP</button>
    </div>
</div>
"""

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("ScholarTube")
    current_user = st.selectbox("Login as:", ["Dr. Miguel", "Prof. Sarah"])
    st.markdown("---")
    page = st.radio("Navigation", ["Home Feed", "Creator Studio", "My Profile"])

# --- 5. PAGE: HOME FEED ---
if page == "Home Feed":
    st.header("Global Research Feed")
    vids = [f for f in os.listdir("uploads") if f.endswith(('.webm', '.mp4'))]
    if not vids:
        st.info("No research trailers published yet.")
    for v in vids:
        parts = v.split('_')
        with st.container(border=True):
            col_icon, col_txt = st.columns([1, 8])
            col_icon.title("🔬")
            with col_txt:
                st.subheader(parts[2].replace('.webm', '') if len(parts) > 2 else v)
                st.caption(f"👤 {parts[0]} | 📑 {parts[1] if len(parts) > 1 else 'Research'}")
                st.video(os.path.join("uploads", v))

# --- 6. PAGE: CREATOR STUDIO ---
elif page == "Creator Studio":
    st.header("🎥 Research Trailer Studio")
    
    doi = st.text_input("1. Enter DOI", placeholder="10.1038/s41586-025-10062-6")
    if doi:
        paper_info = get_paper_metadata(doi)
        if paper_info:
            st.success(f"Verified: {paper_info['title']}")
            st.session_state.current_paper = paper_info

    st.subheader("2. Presentation Controls")
    col_info, col_tools = st.columns([2, 1])
    
    with col_tools:
        st.write("### Control Panel")
        components.html(record_js, height=260)
        
        st.divider()
        st.write("### 📤 Publish")
        final_v = st.file_uploader("Upload recording from Downloads", type="webm")
        if st.button("Publish to Feed") and final_v:
            p = st.session_state.get('current_paper', {'title': 'Paper', 'journal': 'Journal'})
            safe_name = f"{current_user}_{p['journal']}_{p['title'][:20]}.webm".replace(" ", "_")
            with open(os.path.join("uploads", safe_name), "wb") as f:
                f.write(final_v.getbuffer())
            st.success("Published!")

    with col_info:
        st.info("""
        **How to present with PowerPoint:**
        1. **Select Mic:** Pick your preferred input from the list.
        2. **Pop Out Bubble:** Launches your camera into a floating window.
        3. **Record:** Select 'Entire Screen' to capture the bubble and PowerPoint together.
        4. **Present:** Open your PowerPoint slides and start talking.
        5. **Stop:** Return here to finish and download.
        """)

# --- 7. MY PROFILE ---
elif page == "My Profile":
    st.header(f"Profile: {current_user}")
    my_vids = [f for f in os.listdir("uploads") if f.startswith(current_user)]
    for v in my_vids:
        st.video(os.path.join("uploads", v))