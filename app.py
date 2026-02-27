import streamlit as st
import fitz  # This will now be powered by pymupdf-lite
import io
import requests
from PIL import Image
import streamlit.components.v1 as components



# --- 1. CONFIG & STORAGE ---
st.set_page_config(page_title="J-Club", layout="wide")

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
            authors = [f"{a.get('given')} {a.get('family')}" for a in data.get('author', [])]
            journal = data.get('container-title', [''])[0]
            year = data.get('created', {}).get('date-parts', [[0]])[0][0]
            return {
                "title": title,
                "authors": ", ".join(authors[:3]) + ("..." if len(authors) > 3 else ""),
                "journal": f"{journal} ({year})"
            }
    except:
        return None
    return None

# --- 3. JAVASCRIPT MASTER RECORDER ---
record_js = """
<script>
let mediaRecorder;
let recordedChunks = [];

async function startRecording() {
    try {
        const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: { cursor: "always" }, audio: true });
        const voiceStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        const combinedStream = new MediaStream([...screenStream.getVideoTracks(), ...voiceStream.getAudioTracks()]);

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
        alert("🎤 Recording started! Present your slides now.");
    } catch (err) { alert("Recording access denied."); }
}
function stopRecording() { mediaRecorder.stop(); }
</script>
<div style="text-align: center; background: #111; padding: 10px; border-radius: 10px; border: 1px solid #333;">
    <button onclick="startRecording()" style="background:#ff4b4b; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; font-weight:bold;">🔴 START RECORDING</button>
    <button onclick="stopRecording()" style="background:#444; color:white; border:none; padding:10px 20px; border-radius:5px; cursor:pointer; margin-left:10px;">⏹️ STOP & DOWNLOAD</button>
</div>
"""

# --- 4. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("J-Club")
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
        # Format: User_Journal_Title.webm
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
    
    # STEP 1: VERIFIED DOI
    st.subheader("1. Identify Your Paper")
    doi = st.text_input("Enter DOI (e.g., 10.1038/s41586-025-10062-6)")
    
    if doi:
        with st.spinner("Verifying DOI..."):
            paper_info = get_paper_metadata(doi)
            if paper_info:
                st.success("Verified Paper Found!")
                st.session_state.current_paper = paper_info
                st.markdown(f"**Title:** {paper_info['title']}")
                st.markdown(f"**Journal:** {paper_info['journal']}")
                st.markdown(f"**Authors:** {paper_info['authors']}")
            else:
                st.error("DOI not found. Please check the string.")

    # STEP 2: PDF DECOMPOSE
    st.subheader("2. Upload & Decompose")
    uploaded_pdf = st.file_uploader("Upload PDF", type="pdf")
    
    if uploaded_pdf:
        if 'active_slides' not in st.session_state:
            with st.spinner("Rendering High-Res Slides..."):
                doc = fitz.open(stream=uploaded_pdf.read(), filetype="pdf")
                extracted = []
                mat = fitz.Matrix(4.0, 4.0) 
                for page_obj in doc:
                    pix = page_obj.get_pixmap(matrix=mat)
                    extracted.append(Image.open(io.BytesIO(pix.tobytes())))
                st.session_state.active_slides = extracted

        if 'active_slides' in st.session_state:
            col_stage, col_tools = st.columns([3, 1])
            with col_tools:
                st.subheader("Recording")
                components.html(record_js, height=120)
                st.divider()
                idx = st.select_slider("Slide", options=range(len(st.session_state.active_slides)))
                st.camera_input("Narrator Bubble")
                
                # PUBLISH SECTION
                st.divider()
                st.write("### 📤 Publish")
                final_v = st.file_uploader("Upload .webm file", type="webm")
                if st.button("Publish to Feed") and final_v:
                    # Clean filename for the feed
                    p_title = st.session_state.get('current_paper', {}).get('title', 'UnknownTitle')[:30]
                    p_journal = st.session_state.get('current_paper', {}).get('journal', 'UnknownJournal')[:20]
                    safe_name = f"{current_user}_{p_journal}_{p_title}.webm".replace(" ", "")
                    
                    with open(os.path.join("uploads", safe_name), "wb") as f:
                        f.write(final_v.getbuffer())
                    st.success("Published!")
                    # Clear session for next paper
                    del st.session_state['active_slides']

            with col_stage:
                st.image(st.session_state.active_slides[idx], use_container_width=True)

# --- 7. MY PROFILE ---
elif page == "My Profile":
    st.header(f"Profile: {current_user}")
    my_vids = [f for f in os.listdir("uploads") if f.startswith(current_user)]
    if my_vids:
        for v in my_vids:
            st.video(os.path.join("uploads", v))
