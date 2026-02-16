import subprocess
import json

class YouTubePlaylistHandler:
    def __init__(self, url):
        self.url = url

    def fetch_playlist_info(self):
        """Recupera info playlist usando yt-dlp --flat-playlist"""
        cmd = [
            "yt-dlp",
            self.url,
            "--dump-json",
            "--flat-playlist"
        ]

        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        if process.returncode != 0:
            raise Exception(f"Errore recupero playlist: {process.stderr}")

        lines = process.stdout.strip().split('\n')
        
        title = "Playlist sconosciuta"
        video_items = []

        # Tenta di parsare ogni riga come JSON
        for line in lines:
            try:
                data = json.loads(line)
                # Se è una entry video valida
                if "title" in data and "url" in data:
                     video_items.append({
                        'url': data.get("url"),
                        'title': data.get("title")
                    })
                # A volte il primo oggetto è i metadata della playlist
                if "title" in data and "entries" not in data and not video_items:
                    # Fallback titolo se disponibile nel primo oggetto
                    pass 
            except:
                pass
        
        if video_items:
            title = f"Playlist ({len(video_items)} video)"
            
        return title, video_items