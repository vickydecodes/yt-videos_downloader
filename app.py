import streamlit as st
import yt_dlp
import os
import shutil
from pathlib import Path

# ========================= CONFIG =========================
st.set_page_config(page_title="YouTube Downloader", page_icon="📥", layout="centered")

st.title("📥 YouTube Downloader")
st.caption("Powered by yt-dlp • Fast • Reliable • No Ads")

# Use a temporary directory that persists during session (important for Streamlit Cloud)
if "download_dir" not in st.session_state:
    st.session_state.download_dir = "downloads"
    os.makedirs(st.session_state.download_dir, exist_ok=True)

# ========================= UI =========================
url = st.text_input("🔗 Enter YouTube URL (or Shorts, Playlist, etc.)", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns([3, 1])
with col1:
    download_folder = st.text_input(
        "📁 Download folder",
        value=st.session_state.download_dir,
        help="Files will be saved here and available for download"
    )
with col2:
    if st.button("🗑 Open Folder", help="Show downloaded files"):
        if os.path.exists(download_folder):
            st.write("Downloaded files:")
            for file in sorted(Path(download_folder).iterdir()):
                if file.is_file():
                    st.write(f"• {file.name}")
        else:
            st.info("Folder is empty")

download_type = st.radio(
    "Download type",
    ["Video (Best Quality MP4)", "Audio Only (MP3 192kbps)"],
    horizontal=True
)

progress_bar = st.progress(0)
status_text = st.empty()
download_status = st.empty()

# ========================= PROGRESS HOOK =========================
def progress_hook(d):
    if d["status"] == "downloading":
        try:
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total:
                percent = int(downloaded / total * 100)
                progress_bar.progress(percent)
                filename = d.get("filename", "Unknown")
                short_name = os.path.basename(filename)
                status_text.text(f"Downloading: {short_name} — {percent}%")
        except:
            pass
    elif d["status"] == "finished":
        progress_bar.progress(100)
        status_text.text("Download finished! Converting/processing...")
    elif d["status"] == "error":
        status_text.error("An error occurred during download")

# ========================= DOWNLOAD LOGIC =========================
if st.button("⬇️ Start Download", type="primary", use_container_width=True):
    if not url.strip():
        st.warning("Please enter a valid YouTube URL")
        st.stop()

    if not url.startswith(("http://", "https://")):
        st.error("Invalid URL — must start with http:// or https://")
        st.stop()

    # Reset progress
    progress_bar.progress(0)
    status_text.empty()

    try:
        ydl_opts = {
            "outtmpl": os.path.join(download_folder, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": False,
            "continued": True,
            "retries": 10,
            "fragment_retries": 10,
            "extractor_retries": 5,
        }

        if download_type == "Audio Only (MP3 192kbps)":
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
                "postprocessor_args": [
                    "-ar", "44100",           # Better compatibility
                    "-ac", "2"                # Stereo
                ],
                "prefer_ffmpeg": True,
            })
        else:
            # Best compatible MP4 (H.264 + AAC)
            ydl_opts.update({
                "format": "bestvideo[vcodec^=avc1]+bestaudio[acodec^=mp4a]/best",
                "merge_output_format": "mp4",
            })

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        title = info.get("title", "Unknown")
        ext = "mp3" if download_type.startswith("Audio") else "mp4"
        likely_filename = os.path.join(download_folder, f"{title}.{ext}")

        # Find actual downloaded file (yt-dlp may sanitize title)
        downloaded_files = list(Path(download_folder).glob(f"{title}*"))
        if not downloaded_files:
            # Fallback search
            downloaded_files = [f for f in Path(download_folder).iterdir() if f.is_file()]
            downloaded_files = sorted(downloaded_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]

        if downloaded_files:
            file_path = downloaded_files[0]
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"💾 Download: {file_path.name}",
                    data=f,
                    file_name=file_path.name,
                    mime="video/mp4" if ext == "mp4" else "audio/mpeg",
                    use_container_width=True
                )

        st.success(f"✅ Successfully downloaded: **{title}**")
        st.balloons()

    except Exception as e:
        st.error("❌ Download failed!")
        st.exception(e)
        if "private video" in str(e).lower():
            st.info("This video is private or age-restricted.")
        elif "unavailable" in str(e).lower():
            st.info("The video is unavailable or has been removed.")

# ========================= FOOTER =========================
st.markdown("---")
st.markdown(
    """
    <small>
    ⚡ Built with Streamlit + yt-dlp • Supports videos, Shorts, playlists (first 10), live streams (if recorded)<br>
    🔒 Your downloads are private and deleted after session ends on cloud deployments
    </small>
    """,
    unsafe_allow_html=True
)