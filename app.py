from flask import Flask, request, jsonify
import requests
import re
import urllib.parse

app = Flask(__name__)

@app.route('/')
def home():
    url = request.args.get('url')
    
    if not url or "instagram.com/reel/" not in url:
        return jsonify({"status": "error", "message": "Instagram Reel URL required"}), 400
    
    try:
        # Create embed URL
        embed_url = url.split('?')[0].rstrip('/') + '/embed/'
        
        # Proxies
        proxies = [
            "https://api.allorigins.win/raw?url=",
            "https://corsproxy.io/?"
        ]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html",
            "Referer": "https://www.instagram.com/"
        }
        
        for proxy in proxies:
            try:
                proxy_url = proxy + urllib.parse.quote(embed_url)
                response = requests.get(proxy_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Pattern 1: video_url in JSON
                    match1 = re.search(r'"video_url":"([^"]+)"', html)
                    if match1:
                        video_url = match1.group(1).replace('\\/', '/')
                        return jsonify({
                            "status": "success",
                            "url": video_url
                        })
                    
                    # Pattern 2: CDN URL
                    match2 = re.search(r'(https?://[^"\s]+\.fbcdn\.net[^"\s]*\.mp4[^"\s]*)', html)
                    if match2:
                        return jsonify({
                            "status": "success",
                            "url": match2.group(1)
                        })
                    
                    # Pattern 3: video src
                    match3 = re.search(r'video[^>]+src="([^"]+)"', html, re.IGNORECASE)
                    if match3:
                        return jsonify({
                            "status": "success",
                            "url": match3.group(1)
                        })
                    
            except Exception as e:
                continue
        
        return jsonify({"status": "error", "message": "Video not found"}), 404
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
