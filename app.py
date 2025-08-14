import streamlit as st
import yt_dlp
import os
import time
import re
from pathlib import Path

st.set_page_config(
    page_title="YouTube Video Downloader",
    page_icon="▶️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Add custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #FF0000;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    .download-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .format-option {
        background-color: #f1f3f4;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to clean ANSI escape codes
def clean_ansi_codes(text):
    """Remove ANSI escape codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# Helper functions (defined before they're used)
def get_available_formats(url):
    """Get available video formats for the given YouTube URL"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        formats = info_dict.get('formats', [])
        
        # Filter for video formats that include audio or can be combined with audio
        video_formats = []
        
        # First, add formats that already include both video and audio
        for f in formats:
            if (f.get('vcodec') != 'none' and f.get('acodec') != 'none' and 
                f.get('height')):
                format_id = f.get('format_id')
                resolution = f"{f.get('height')}p"
                fps = f.get('fps', '')
                if fps:
                    resolution += f" ({fps}fps)"
                extension = f.get('ext')
                file_size = f.get('filesize')
                size_str = ""
                if file_size:
                    size_str = f" ({file_size/1024/1024:.1f}MB)"
                video_formats.append({
                    'format_id': format_id,
                    'resolution': resolution,
                    'extension': extension,
                    'size': size_str,
                    'has_audio': True
                })
        
        # Then, add video-only formats that can be combined with audio
        for f in formats:
            if (f.get('vcodec') != 'none' and f.get('acodec') == 'none' and 
                f.get('height')):
                format_id = f.get('format_id')
                resolution = f"{f.get('height')}p"
                fps = f.get('fps', '')
                if fps:
                    resolution += f" ({fps}fps)"
                extension = f.get('ext')
                file_size = f.get('filesize')
                size_str = ""
                if file_size:
                    size_str = f" ({file_size/1024/1024:.1f}MB)"
                video_formats.append({
                    'format_id': format_id,
                    'resolution': resolution,
                    'extension': extension,
                    'size': size_str,
                    'has_audio': False
                })
    
    # Remove duplicates and sort by resolution (highest first)
    unique_formats = {}
    for f in video_formats:
        key = f"{f['resolution']}_{f['extension']}"
        if key not in unique_formats:
            unique_formats[key] = f
    
    # Sort by resolution (height)
    sorted_formats = sorted(
        unique_formats.values(), 
        key=lambda x: int(x['resolution'].split('p')[0].split(' ')[0]), 
        reverse=True
    )
    
    return sorted_formats, info_dict.get('title', 'Unknown Title')

def download_video(url, format_choice, output_path='.', progress_hook=None):
    """Download the video with the selected format"""
    ydl_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        }
    }
    
    if progress_hook:
        ydl_opts['progress_hooks'] = [progress_hook]
    
    if format_choice == "best":
        # Auto select best quality with audio
        ydl_opts['format'] = 'bestvideo+bestaudio/best'
    else:
        # User selected format - ensure audio is included
        if format_choice['has_audio']:
            # Format already includes audio
            format_id = format_choice['format_id']
        else:
            # Video-only format, need to add audio
            format_id = f"{format_choice['format_id']}+bestaudio"
        
        ydl_opts['format'] = format_id
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info_dict)
        return filename

# App title and description
st.markdown("<h1 class='main-header'>📺 YouTube Video Downloader</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Download YouTube videos with your preferred resolution</p>", unsafe_allow_html=True)

# Initialize session state variables
if 'video_info' not in st.session_state:
    st.session_state.video_info = None
if 'download_path' not in st.session_state:
    st.session_state.download_path = None
if 'download_success' not in st.session_state:
    st.session_state.download_success = False
if 'error_message' not in st.session_state:
    st.session_state.error_message = None

# Create sidebar for settings
with st.sidebar:
    # Main Settings Header
    st.markdown("<div style='font-size:24px; font-weight:bold;'>⚙ Settings</div>", unsafe_allow_html=True)

    # Output Directory Section
    st.markdown("<div style='font-size:22px; margin-top:20px;'>📁 Output Directory</div>", unsafe_allow_html=True)
    output_dir = st.text_input("Enter download folder path:", value="./downloads")

    st.markdown("<hr>", unsafe_allow_html=True)

    # Help Section Header
    st.markdown("<div style='font-size:22px;'>❓ Help</div>", unsafe_allow_html=True)

    # Highlighted ytdlp Info
    st.markdown("""
    <div style='
        background-color:#f0f8ff;
        padding:15px;
        border-radius:8px;
        font-size:20px;
        margin-top:10px;
        border-left: 5px solid #3399ff;
    '>
        This app uses <strong>yt-dlp</strong>, which is more reliable for downloading from YouTube.
    </div>
    """, unsafe_allow_html=True)

    # Update Command
    st.markdown("<div style='font-size:20px; margin-top:15px;'><strong>To update yt-dlp:</strong></div>", unsafe_allow_html=True)

    st.code("pip install --upgrade yt-dlp", language="bash")



# Main content area
with st.container():
    # URL input
    st.markdown("### Enter YouTube Video URL")
    url = st.text_input("Enter YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
    
    # Fetch formats button
    if st.button("Fetch Available Formats", type="primary"):
        if not url:
            st.error("Please enter a YouTube URL")
        else:
            # Progress bar for fetching formats
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate progress
            for i in range(100):
                progress_bar.progress(i + 1)
                status_text.text(f"Fetching formats... {i+1}%")
                time.sleep(0.01)
            
            try:
                # Get available formats
                formats, title = get_available_formats(url)
                
                if formats:
                    st.session_state.video_info = {
                        'url': url,
                        'title': title,
                        'formats': formats
                    }
                    st.success(f"Found {len(formats)} format options for: {title}")
                else:
                    st.error("No video formats found. The video might be private or unavailable.")
                    st.session_state.video_info = None
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
                st.session_state.video_info = None
    
    # Display video information and format selection if available
    if st.session_state.video_info:
        video_info = st.session_state.video_info
        
        with st.container():
            st.markdown("### Video Information")
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Title:** {video_info['title']}")
            
            with col2:
                if st.button("Clear", key="clear_button"):
                    st.session_state.video_info = None
                    st.rerun()
        
        st.markdown("### Select Resolution")
        
        # Format selection
        format_options = []
        format_labels = []
        
        # Add "Best Quality" option
        format_options.append("best")
        format_labels.append("Best Available Quality (Auto)")
        
        for fmt in video_info['formats']:
            audio_status = "✓" if fmt['has_audio'] else "+ audio"
            label = f"{fmt['resolution']} ({fmt['extension']}) {audio_status} {fmt['size']}"
            format_options.append(fmt)
            format_labels.append(label)
        
        # Use selectbox with labels only
        selected_label = st.selectbox("Choose resolution", format_labels)
        selected_format = format_options[format_labels.index(selected_label)]
        
        # Download button
        if st.button("Download Video", type="primary"):
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Progress bar for download
            progress_bar = st.progress(0)
            status_text = st.empty()
            file_size_text = st.empty()
            
            # Custom progress hook for Streamlit
            def progress_hook(d):
                if d['status'] == 'downloading':
                    # Extract percentage and clean ANSI codes
                    percent_str = d.get('_percent_str', '0%').strip()
                    percent_str = clean_ansi_codes(percent_str)
                    
                    # Convert to float safely
                    try:
                        percent = float(percent_str.replace('%', ''))
                    except (ValueError, AttributeError):
                        percent = 0
                    
                    progress_bar.progress(percent / 100)
                    
                    # Extract speed and ETA (clean ANSI codes)
                    speed = clean_ansi_codes(d.get('_speed_str', 'N/A').strip())
                    eta = clean_ansi_codes(d.get('_eta_str', 'N/A').strip())
                    status_text.text(f"Downloading: {percent_str} | Speed: {speed} | ETA: {eta}")
                    
                    # Extract file size
                    total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate')
                    if total_bytes:
                        file_size_text.text(f"File size: {total_bytes / 1024 / 1024:.2f} MB")
                
                elif d['status'] == 'finished':
                    progress_bar.progress(100)
                    status_text.text("Download completed!")
                    file_size_text.text(f"File saved as: {d['filename']}")
            
            try:
                # Download the video
                download_path = download_video(
                    video_info['url'], 
                    selected_format, 
                    output_dir,
                    progress_hook
                )
                
                st.session_state.download_path = download_path
                st.session_state.download_success = True
                st.session_state.error_message = None
                
            except Exception as e:
                st.session_state.download_success = False
                st.session_state.error_message = str(e)
                
            # Rerun to show download result
            st.rerun()
    
    # Display download result
    if st.session_state.download_success:
        st.markdown(
            f"""
            <div style='color: green; background-color: #d4edda; padding: 12px; border-radius: 6px;
                        font-size: 20px; font-weight: bold; margin-bottom: 10px;'>
                ✅ Download completed successfully!<br>
                Video saved to: {st.session_state.download_path}
            </div>
            """,
            unsafe_allow_html=True
        )


        
        # # Provide download button
        # if os.path.exists(st.session_state.download_path):
        #     with open(st.session_state.download_path, 'rb') as f:
        #         st.download_button(
        #             label="Download Video File",
        #             data=f,
        #             file_name=os.path.basename(st.session_state.download_path),
        #             mime="video/mp4"
        #         )
    
    if st.session_state.error_message:
        st.markdown(f"""
        <div class="error-message">
            Error: {st.session_state.error_message}
        </div>
        """, unsafe_allow_html=True)

