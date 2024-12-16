from flask import Flask, render_template, request, jsonify
import requests
import config
import lyricsgenius
import openai

app = Flask(__name__)

# Get Genius API access token from config
GENIUS_ACCESS_TOKEN = config.GENIUS_ACCESS_TOKEN

# Get OpenAI API key from config
OPENAI_API_KEY = config.OPENAI_API_KEY

# Initialize Genius API
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)

# Read examples from a text file with UTF-8 encoding
with open('examples.txt', 'r', encoding='utf-8') as file:
    example_json = file.read()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search_page():
    return render_template("search.html")

@app.route("/lyrics")
def lyrics_page():
    return render_template("lyrics.html")

@app.route("/analysis")
def analysis_page():
    return render_template("analysis.html")

@app.route("/api/search", methods=["GET"])
def api_search():
    query = request.args.get("query", "")
    if not query:
        return jsonify({"error": "No search query provided"}), 400

    headers = {
        "Authorization": f"Bearer {GENIUS_ACCESS_TOKEN}"
    }
    url = f"https://api.genius.com/search?q={query}"
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        return jsonify({"error": f"Error fetching data from Genius API: {err}"}), response.status_code

    data = response.json()
    return jsonify(data.get("response", {}).get("hits", []))

@app.route("/api/lyrics", methods=["GET"])
def api_lyrics():
    artist = request.args.get("artist", "")
    title = request.args.get("title", "")
    if not artist or not title:
        return jsonify({"error": "Please provide both artist and song title"}), 400
    
    try:
        url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(title)}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "lyrics" in data:
            return jsonify({"lyrics": data["lyrics"]}), 200
        else:
            return jsonify({"error": "Lyrics not found"}), 404
    except Exception as e:
        # Log the error for debugging
        print("Error fetching lyrics:", str(e))
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json()
    lyrics = data.get("lyrics", "")
    if not lyrics:
        return jsonify({"error": "No lyrics provided"}), 400

    openai.api_key = config.OPENAI_API_KEY
    messages = [
        {"role": "system", "content": "You analyze song lyrics."},
        {"role": "assistant", "content": example_json.split("###")[0]},  # Use only the first example
        {"role": "user", "content": f"Analyze these lyrics:\n\n{lyrics}"}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=1000  # Adjust max_tokens to ensure the response fits within the limit
        )
        analysis = response.choices[0].message["content"].strip()
        
        # Log the response for debugging
        print("OpenAI API response:", response)
        
        return jsonify({"analysis": analysis})
    except Exception as e:
        # Log the error for debugging
        print("Error:", str(e))
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/api/generate_prompt", methods=["POST"])
def api_generate_prompt():
    data = request.get_json()
    analysis = data.get("analysis", "")
    if not analysis:
        return jsonify({"error": "No analysis provided"}), 400

    openai.api_key = config.OPENAI_API_KEY
    messages = [
        {"role": "system", "content": "You create prompts for DALL-E based on song analysis."},
        {"role": "user", "content": f"Create a DALL-E prompt based on the following analysis:\n\n{analysis}"}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=100
        )
        prompt = response.choices[0].message["content"].strip()
        
        # Log the response for debugging
        print("OpenAI API response:", response)
        
        return jsonify({"prompt": prompt})
    except Exception as e:
        # Log the error for debugging
        print("Error generating prompt:", str(e))
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/api/generate_image", methods=["POST"])
def api_generate_image():
    data = request.get_json()
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400

    openai.api_key = config.OPENAI_API_KEY
    try:
        response = openai.Image.create(
            prompt=prompt,
            model="dall-e-3"
        )
        
        # Log the response for debugging
        print("DALL-E API response:", response)
        
        return jsonify({"image_url": response['data'][0]['url']})
    except Exception as e:
        # Log the error for debugging
        print("Error generating image:", str(e))
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
