import subprocess
import json

class YouTubeVideoHandler:
    def __init__(self, url):
        self.url = url
        self.video_info = {}
        self.formats_map = {}
        self.title = "Unknown"

    def fetch_info(self):
        """Recupera metadati e risoluzioni usando yt-dlp --dump-json"""
        cmd = [
            "yt-dlp", 
            self.url, 
            "--dump-json", 
            "--no-playlist"
        ]
        
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
        
        formats = self.video_info.get("formats", [])
        self.formats_map = {}
        
        for f in formats:
            height = f.get("height")
            vcodec = f.get("vcodec")
            
            if height and vcodec != "none":
                res_key = f"{height}p"
                self.formats_map[res_key] = f["format_id"]

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
