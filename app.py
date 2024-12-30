"""
Flask Backend for Torrent Management
-------------------------------------
This backend provides endpoints for:
1. Scraping torrent results from a website using requests and BeautifulSoup.
2. Interfacing with qBittorrent Web API to fetch and manage torrents.
"""

import time
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from qbittorrent import Client
import configparser
import logging
import sys

# -------- CONFIGURATION SETUP -------- #

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Load the configuration file
config = configparser.ConfigParser()
config.read('config.ini')

# qBittorrent credentials and host
try:
    qb_host = config.get('qbit', 'host')
    qb_user = config.get('qbit', 'user')
    qb_pass = config.get('qbit', 'pass')
    
    # Validate credentials
    if not qb_host or qb_host.lower() == 'http://host_ip:port':
        logger.error("Invalid 'host' in 'config.ini'. Please set a valid qBittorrent host.")
        raise ValueError("Invalid 'host' in 'config.ini'. Please set a valid qBittorrent host.")
    if not qb_user:
        logger.error("Invalid 'user' in 'config.ini'. Please set a valid qBittorrent username.")
        raise ValueError("Invalid 'user' in 'config.ini'. Please set a valid qBittorrent username.")
    if not qb_pass:
        logger.error("Invalid 'pass' in 'config.ini'. Please set a valid qBittorrent password.")
        raise ValueError("Invalid 'pass' in 'config.ini'. Please set a valid qBittorrent password.")

    logger.info("Configuration loaded successfully.")

except configparser.NoSectionError as e:
    logger.error("Missing section in 'config.ini': %s", e)
    sys.exit(1)
except configparser.NoOptionError as e:
    logger.error("Missing option in 'config.ini': %s", e)
    sys.exit(1)
except ValueError as e:
    logger.error("Configuration validation error: %s", e)
    sys.exit(1)
except Exception as e:
    logger.error("Unexpected error while reading 'config.ini': %s", e)
    sys.exit(1)

# Initialize qBittorrent client
try:
    logger.info("Initializing qBittorrent client by establishing a connection to %s", qb_host)
    qb = Client(qb_host)
except Exception as e:
    logger.error("Error initializing qBittorrent client: %s", e)
    sys.exit("Fatal error: Unable to initialize qBittorrent client. Exiting.")

# Initialize Flask application
app = Flask(__name__)

# -------- HELPER FUNCTIONS -------- #


# If bitsearch.to fully dies I will rewrite the search function to use a different website
def scrape_website(search_query):
    """
    Scrapes the torrent website for results matching the search query.

    Args:
        search_query (str): The search term to query the website.

    Returns:
        list: A list of dictionaries containing torrent details.
    """
    logger.info("Starting scrape for query: %s", search_query)
    url = f"https://bitsearch.to/search?q={search_query}&category=1&subcat=2"
    attempts = 3
    response = None

    for attempt in range(1, attempts + 1):
        try:
            logger.info("Attempt %d of %d for URL: %s", attempt, attempts, url)
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()  # Raise an exception for HTTP errors
            break  # Exit the loop if the request is successful
        except requests.RequestException as e:
            logger.error("Attempt %d failed for URL %s: %s", attempt, url, e)
            if attempt < attempts:
                time.sleep(1)  # Wait 1 second before retrying
            else:
                logger.error("All %d attempts failed. Returning empty result.", attempts)
                return []  # Return an empty list if all attempts fail

    # Parse the response with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')
    results = []
    for item in soup.select('.card.search-result.my-2'):
        try:
            magnet_link = item.select_one('.dl-magnet')['href'] if item.select_one('.dl-magnet') else None
            title_element = item.select_one('.title a')
            title = title_element.text.strip() if title_element else "Title not found"
            link = title_element['href'] if title_element else "Link not found"
            category = item.select_one('.category').text.strip() if item.select_one('.category') else "Category not found"
            size = item.select_one('.stats img[alt="Size"]').parent.text.strip() if item.select_one('.stats img[alt="Size"]') else "Size not found"
            seeders = item.select_one('.stats img[alt="Seeder"]').parent.text.strip() if item.select_one('.stats img[alt="Seeder"]') else "Seeders not found"
            leechers = item.select_one('.stats img[alt="Leecher"]').parent.text.strip() if item.select_one('.stats img[alt="Leecher"]') else "Leechers not found"
            date = item.select_one('.stats img[alt="Date"]').parent.text.strip() if item.select_one('.stats img[alt="Date"]') else "Date not found"

            if magnet_link:
                results.append({
                    'title': title,
                    'link': link,
                    'category': category,
                    'size': size,
                    'seeders': seeders,
                    'leechers': leechers,
                    'date': date,
                    'magnet_link': magnet_link
                })

                if len(results) >= 5:  # Limit to the first 5 results
                    break
        except Exception as e:
            logger.error("Error parsing a result item: %s", e)
            continue

    logger.info("Scraping complete. Found %d results.", len(results))
    return results


# -------- API ENDPOINTS -------- #

@app.route('/torrents', methods=['GET'])
def torrents():
    """
    Endpoint to search for torrents using a query string.

    Query Parameters:
        q (str): The search query.

    Returns:
        JSON: List of torrent results or an error message.
    """
    query = request.args.get('q', '').strip()
    if not query:
        logger.warning("No query provided in request.")
        return jsonify({'error': 'No query provided'}), 400

    logger.info("Received request to search for torrents with query: %s", query)
    results = scrape_website(query)
    return jsonify(results), 200

@app.route('/infoglobal', methods=['GET'])
def get_filtered_torrents():
    """
    Endpoint to fetch information about active torrents from qBittorrent.

    Returns:
        JSON: A list of active torrents or an error message.
    """
    if not qb:
        logger.error("qBittorrent client is not initialized.")
        return jsonify({"error": "qBittorrent client is unavailable."}), 503

    try:
        qb.login(qb_user, qb_pass)
        filters = {'filter': 'downloading', 'sort': 'time_active', 'limit': 10, 'offset': 0}
        torrent_list = qb.torrents(**filters)

        # Cache the last torrent count and time to avoid repetitive logs
        if not hasattr(get_filtered_torrents, "last_torrent_count"):
            get_filtered_torrents.last_torrent_count = None
        if not hasattr(get_filtered_torrents, "last_log_time"):
            get_filtered_torrents.last_log_time = 0

        current_time = time.time()
        log_interval = 60  # Log summary every 60 seconds

        if isinstance(torrent_list, list):
            active_torrent_count = len(torrent_list)
            
            # Log only if the count changes or the log interval has passed
            if (active_torrent_count != get_filtered_torrents.last_torrent_count or
                current_time - get_filtered_torrents.last_log_time > log_interval):
                
                get_filtered_torrents.last_log_time = current_time
                get_filtered_torrents.last_torrent_count = active_torrent_count
                
                if active_torrent_count > 0:
                    logger.info("Currently %d active torrents.", active_torrent_count)
                else:
                    logger.info("No active torrents currently downloading.")

            return jsonify(torrent_list), 200

        else:
            logger.error("Unexpected response from qBittorrent API.")
            return jsonify({"error": "Unexpected response from qBittorrent API"}), 500

    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500


# -------- MAIN -------- #

if __name__ == '__main__':
    logger.info("Running directly with Flask development server.")
    app.run(host='0.0.0.0', port=5000, debug=True)  # Use Flask's built-in server
else:
    logger.info("Running with gunicorn deployment server.")
    logger.info("Gunicorn entry point detected, Backend is up and ready to go.")
