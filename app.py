from flask import Flask, request, jsonify
import requests
import re
import json
import urllib.parse

app = Flask(__name__)

@app.route('/')
def get_video():
    url = request.args.get('url')
    
    if not url or "instagram.com/reel/" not in url:
        return jsonify({
            "status": "error", 
            "message": "Instagram Reel URL required"
        }), 400
    
    try:
        # METHOD 1: Try direct API call (Latest method)
        reel_id = extract_reel_id(url)
        if reel_id:
            api_response = try_direct_api(reel_id)
            if api_response:
                return jsonify({
                    "status": "success",
                    "url": api_response,
                    "method": "direct_api"
                })
        
        # METHOD 2: Try embed page with new selectors
        embed_response = try_embed_method(url)
        if embed_response:
            return jsonify({
                "status": "success",
                "url": embed_response,
                "method": "embed_page"
            })
        
        # METHOD 3: Try alternative services
        alt_response = try_alternative_services(url)
        if alt_response:
            return jsonify({
                "status": "success",
                "url": alt_response,
                "method": "alternative"
            })
        
        return jsonify({
            "status": "error",
            "message": "Video not found. Instagram may have updated their API."
        }), 404
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Server error: {str(e)}"
        }), 500

def extract_reel_id(url):
    """Extract reel ID from URL"""
    patterns = [
        r'instagram\.com/reel/([^/?]+)',
        r'instagram\.com/p/([^/?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def try_direct_api(reel_id):
    """Try Instagram's GraphQL API"""
    try:
        api_url = f"https://www.instagram.com/p/{reel_id}/?__a=1&__d=dis"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.instagram.com/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Navigate through Instagram's JSON structure
            if 'graphql' in data:
                media = data['graphql']['shortcode_media']
                if 'video_url' in media:
                    return media['video_url']
                elif 'video_versions' in media:
                    return media['video_versions'][0]['url']
            
            # Alternative structure
            if 'items' in data:
                for item in data['items']:
                    if 'video_versions' in item:
                        return item['video_versions'][0]['url']
                    
    except Exception as e:
        print(f"Direct API failed: {e}")
    
    return None

def try_embed_method(url):
    """Try embed page with updated selectors"""
    try:
        # Create embed URL
        clean_url = url.split('?')[0].rstrip('/')
        embed_url = f"{clean_url}/embed/captioned/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.instagram.com/"
        }
        
        response = requests.get(embed_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # New patterns for 2024 Instagram
            patterns = [
                # JSON-LD data
                r'"contentUrl":"([^"]+\.mp4[^"]*)"',
                # Video source
                r'source src="([^"]+\.mp4[^"]*)"',
                # Video URL in meta
                r'property="og:video" content="([^"]+)"',
                # Instagram's new data structure
                r'video_url":"([^"]+)"',
                # Direct CDN URL
                r'(https?://[^"\s]+\.(fbcdn|cdninstagram)\.(net|com)[^"\s]*\.mp4[^"\s]*)',
                # Base64 encoded data
                r'data-video="([^"]+)"',
                # Instagram's GraphQL response in HTML
                r'"video_versions":\[\{"url":"([^"]+)"',
                # Additional patterns
                r'"display_url":"([^"]+)"',
                r'video src="([^"]+)"',
                r'content="([^"]+\.mp4[^"]*)"'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    # Clean URL
                    video_url = match.replace('\\/', '/').replace('\\u0026', '&')
                    
                    # Validate URL
                    if video_url.startswith('http') and '.mp4' in video_url.lower():
                        print(f"Found URL with pattern: {pattern[:30]}...")
                        return video_url
            
            # Try to find JSON data in script tags
            script_pattern = r'<script[^>]*>([^<]*)</script>'
            scripts = re.findall(script_pattern, html, re.IGNORECASE)
            
            for script in scripts:
                if 'video_versions' in script or 'video_url' in script:
                    try:
                        # Extract JSON-like data
                        json_match = re.search(r'({.*})', script)
                        if json_match:
                            data = json.loads(json_match.group(1))
                            
                            # Try different JSON paths
                            if 'video_url' in data:
                                return data['video_url']
                            elif 'video_versions' in data and len(data['video_versions']) > 0:
                                return data['video_versions'][0]['url']
                            elif 'graphql' in data:
                                media = data['graphql']['shortcode_media']
                                if 'video_url' in media:
                                    return media['video_url']
                                elif 'video_versions' in media:
                                    return media['video_versions'][0]['url']
                    except:
                        continue
        
    except Exception as e:
        print(f"Embed method failed: {e}")
    
    return None

def try_alternative_services(url):
    """Try third-party services as fallback"""
    try:
        services = [
            {
                'name': 'ddinstagram',
                'url': f"https://www.ddinstagram.com/p/{extract_reel_id(url)}/",
                'pattern': r'source src="([^"]+\.mp4[^"]*)"'
            },
            {
                'name': 'instasupersave',
                'api': 'https://instasupersave.com/api/ig/',
                'method': 'POST'
            }
        ]
        
        for service in services:
            try:
                if service['name'] == 'ddinstagram':
                    response = requests.get(service['url'], timeout=10)
                    if response.status_code == 200:
                        match = re.search(service['pattern'], response.text)
                        if match:
                            return match.group(1)
                
                elif service['name'] == 'instasupersave':
                    data = {'url': url}
                    response = requests.post(service['api'], json=data, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'url' in data:
                            return data['url']
                            
            except:
                continue
                
    except Exception as e:
        print(f"Alternative services failed: {e}")
    
    return None

if __name__ == '__main__':
    app.run(debug=True)
