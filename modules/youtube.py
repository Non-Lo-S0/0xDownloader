import subprocess
import json

class YouTubeVideoHandler:
    def __init__(self, url):
        self.url = url
        self.video_info = {}
        self.formats_map = {} # Mappa '1080p' -> 'format_id' (es. '137')
        self.title = "Unknown"

    def fetch_info(self):
        """Recupera metadati e risoluzioni usando yt-dlp --dump-json"""
        cmd = [
            "yt-dlp", 
            self.url, 
            "--dump-json", 
            "--no-playlist"
        ]
        
        # Esegui comando (subprocess, come in downloader.py)
        process = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8'
        )
        
        if process.returncode != 0:
            raise Exception(f"Errore yt-dlp: {process.stderr}")

        self.video_info = json.loads(process.stdout)
        self.title = self.video_info.get("title", "Video senza titolo")
        
        # Estrai formati video
        formats = self.video_info.get("formats", [])
        self.formats_map = {}
        
        for f in formats:
            # Filtra solo video validi con risoluzione
            height = f.get("height")
            vcodec = f.get("vcodec")
            
            # Escludiamo video senza codec o audio-only per la mappa risoluzioni
            if height and vcodec != "none":
                res_key = f"{height}p"
                # yt-dlp ordina dal peggiore al migliore, quindi sovrascrivendo
                # teniamo l'ID con bitrate migliore per quella risoluzione
                self.formats_map[res_key] = f["format_id"]

        # Ordina le risoluzioni (dalla più alta alla più bassa)
        sorted_resolutions = sorted(
            self.formats_map.keys(), 
            key=lambda x: int(x.replace('p', '')), 
            reverse=True
        )

        return sorted_resolutions, self.title

    def get_format_id_for_resolution(self, resolution):
        """Ritorna l'ID del formato video per la risoluzione scelta"""
        return self.formats_map.get(resolution, "best")
    
    @property
    def yt_obj(self):
        """Compatibility property per mantenere il codice esistente nel main"""
        class InfoContainer:
            def __init__(self, title):
                self.title = title
        return InfoContainer(self.title)