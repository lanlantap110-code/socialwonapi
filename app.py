from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.options import Options
from fake_useragent import UserAgent

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

def extract_with_selenium(instagram_url):
    """Launches a headless browser, loads the page, and captures video URLs from network logs."""
    try:
        # 1. Set up a realistic, rotating User-Agent
        ua = UserAgent()
        user_agent = ua.chrome  # or ua.random[citation:7]
        
        # 2. Configure Chrome to run headlessly and log network performance
        capabilities = DesiredCapabilities.CHROME
        capabilities["goog:loggingPrefs"] = {"performance": "ALL"}[citation:3][citation:8]
        
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
        chrome_options.add_argument(f"user-agent={user_agent}")[citation:7]
        
        # 3. Add a proxy (like AllOrigins) if needed. This is complex with Selenium.
        #    You would typically route traffic through a proxy server, not a CORS proxy URL.
        #    Example: chrome_options.add_argument('--proxy-server=http://your-proxy-server:port')
        
        # 4. Initialize the WebDriver with the above settings
        driver = webdriver.Chrome(options=chrome_options, desired_capabilities=capabilities)
        video_urls_found = []
        
        try:
            # 5. Navigate to the Instagram embed page (or direct page)
            # Convert the URL to an embed page if needed
            if '/reel/' in instagram_url and not instagram_url.endswith('/embed/'):
                target_url = instagram_url.rstrip('/') + '/embed/'
            else:
                target_url = instagram_url
                
            driver.get(target_url)
            # Wait for page to load and video to start playing automatically
            time.sleep(5)
            
            # 6. Get all network performance logs
            logs = driver.get_log("performance")[citation:3][citation:8]
            
            # 7. Parse logs to find video file requests
            for log_entry in logs:
                log_data = json.loads(log_entry["message"])["message"]
                
                # Filter for network request/response events
                if ("Network.request" in log_data["method"] or 
                    "Network.response" in log_data["method"]):
                    
                    # Safely get the request URL
                    request_info = log_data.get("params", {}).get("request", {})
                    request_url = request_info.get("url", "")
                    
                    # Look for direct video file URLs (e.g., .mp4 from Facebook's CDN)
                    if request_url and ('.mp4' in request_url or 'video_mp4' in request_url):
                        # Filter out blob URLs and common non-video resources[citation:3]
                        if not request_url.startswith('blob:') and 'fbcdn.net' in request_url:
                            video_urls_found.append(request_url)
                            
        finally:
            # 8. Always quit the driver to free resources
            driver.quit()
            
        # Return the first (likely highest quality) video URL found
        if video_urls_found:
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for url in video_urls_found:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
            return {"status": "success", "url": unique_urls[0]}
        else:
            return {"status": "error", "message": "No video URL found in network traffic."}
            
    except Exception as e:
        return {"status": "error", "message": f"Selenium automation failed: {str(e)}"}

@app.route('/fetch', methods=['GET'])
def fetch_reel():
    """API endpoint to fetch an Instagram Reel's direct video URL."""
    url = request.args.get('url')
    
    if not url or "instagram.com" not in url:
        return jsonify({"status": "error", "message": "A valid Instagram URL is required."}), 400
    
    result = extract_with_selenium(url)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
