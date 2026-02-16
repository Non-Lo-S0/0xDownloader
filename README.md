<div align="center">

  <!-- PROJECT LOGO -->
  <br />
  <img src="https://cdn-icons-png.flaticon.com/512/1384/1384060.png" alt="Logo" width="100" height="100">
  
  <h1 align="center">0xDownloader</h1>

  <p align="center">
    <b>A smart, self-updating YouTube video & audio downloader built with Python and Tkinter.</b>
    <br />
    <br />
    <a href="#key-features">Key Features</a>
    ·
    <a href="#installation">Installation</a>
    ·
    <a href="#usage">Usage</a>
    ·
    <a href="#structure">Structure</a>
  </p>

  <!-- BADGES -->
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/GUI-Tkinter-239120?style=for-the-badge&logo=python&logoColor=white" alt="Tkinter">
    <img src="https://img.shields.io/badge/Engine-yt--dlp-FF0000?style=for-the-badge&logo=youtube&logoColor=white" alt="yt-dlp">
    <img src="https://img.shields.io/badge/Status-Active-success?style=for-the-badge" alt="Status">
  </p>
</div>

<br />

## 📖 About The Project

**0xDownloader** is a robust desktop application designed to simplify downloading high-quality video and audio from YouTube. Unlike simple scripts, it features a complete **GUI ecosystem** that manages its own dependencies, handles network throttling, and ensures you always have the latest tools.

It includes a dedicated **Launch System** (`checker.py`) that scans your environment on startup, repairs missing libraries (PIP, packages), and updates components automatically before the main application (`main.py`) ever runs.

---

<div id="key-features"></div>

## ✨ Key Features

### 🛡️ Smart Dependency Management
- **Self-Healing:** Automatically detects and installs missing Python packages or PIP.
- **Auto-Update:** Checks for updates to core libraries (like `yt-dlp`) on every launch to ensure compatibility with YouTube's latest changes.

### 🚀 Advanced Downloading Engine
- **Throttling Bypass:** Built-in `ThrottleManager` detects YouTube rate limits (429 errors) and applies smart exponential backoff to resume downloads seamlessly.
- **High Quality:** Merges the best available video stream with the best audio stream using `FFmpeg`.
- **Resumable:** Handles network interruptions and file access retries automatically.

### 🎨 Modern UI (Dark Mode)
- **Sleek Interface:** Designed with a dark theme and modern fonts.
- **Visual Feedback:** Progress bars, speed indicators, ETA, and status animations.
- **Splash Screen:** A "MiniSplashLauncher" that verifies system integrity while the app loads.

---

<div id="installation"></div>

## ⚙️ Installation

### Prerequisites
* **Python 3.8+**
* **FFmpeg** (Required for merging video/audio streams)
  * [Download Build](https://gyan.dev/ffmpeg/builds/)

### Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/0xDownloader.git


<h1 align="center">⚡ 0xDownloader</h1>

<p align="center">
  <b>Modern YouTube video & audio downloader</b><br>
  Tkinter GUI • Smooth animations • Smart throttling & auto-updater
</p>

<hr>

<h2>✨ Features</h2>

<ul>
  <li>Clean Tkinter GUI with animated progress ring and live speed/ETA cards.</li>
  <li>Supports YouTube video resolutions and high-quality audio-only downloads.</li>
  <li>Automatic folder management and post-download open-folder shortcut.</li>
  <li>Throttling-aware engine with exponential backoff and retry logic.</li>
  <li>Integrated launcher with splash screen, PIP check, and dependency auto-updater.</li>
</ul>

<h2>📦 Requirements</h2>

<ul>
  <li>Python 3.10+ (recommended)</li>
  <li><code>yt-dlp</code>, <code>ffmpeg</code>, and other packages from <code>requirements.txt</code></li>
</ul>

<h2>🚀 Installation</h2>

<pre>
git clone https://github.com/&lt;your-username&gt;/0xDownloader.git
</pre>

<h2>▶️ Usage</h2>

<ol>
  <li>Run <code>python main.py</code> (it will trigger the checker and updater if needed).</li>
  <li>Paste a YouTube URL in the input field.</li>
  <li>Click <b>⚡ ANALYZE</b> and select the desired quality (video or audio).</li>
  <li>Watch progress, then click <b>📂 OPEN FOLDER</b> when the download is complete.</li>
</ol>

<h2>⚙️ Structure</h2>

<ul>
  <li><code>config.py</code> – global settings (window, colors, layout, engine parameters).</li>
  <li><code>interface.py</code> – main Tkinter GUI and user interactions.</li>
  <li><code>logic.py</code> – download core using <code>yt-dlp</code>, progress & throttling.</li>
  <li><code>utils.py</code> – filesystem helpers, logging bridge, cleanup utilities.</li>
  <li><code>checker.py</code> – splash launcher, PIP and dependency scanner.</li>
  <li><code>updater.py</code> – auto-updater UI and package installation logic.</li>
  <li><code>main.py</code> – entry point that coordinates checker and GUI startup.</li>
</ul>

<hr>

<p align="center">
  <i>IMore sites supports in the future :)</i>
</p>

