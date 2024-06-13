from flask import Flask, request, jsonify
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from qbittorrent import Client
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

qb_host = config.get('qbit', 'host')
qb_user = config.get('qbit', 'user')
qb_pass = config.get('qbit', 'pass')

qb = Client(qb_host)
app = Flask(__name__)

def scrape_website(search_query):
    # Set up the Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--headless')  # Enable headless mode
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)

    # Construct the URL
    url = f"https://bitsearch.to/search?q={search_query}&category=1&subcat=2"
    driver.get(url)

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    driver.quit()

    # Extract data
    results = []
    for item in soup.select('.card.search-result.my-2'):
        # Failsafe for magnet link
        magnet_link_element = item.select_one('.dl-magnet')
        if not magnet_link_element:
            continue
        magnet_link = magnet_link_element['href']

        # Failsafe for title
        title_element = item.select_one('.title a')
        title = title_element.text.strip() if title_element else "Title not found"

        # Failsafe for link
        link = title_element['href'] if title_element else "Link not found"

        # Failsafe for category
        category_element = item.select_one('.category')
        category = category_element.text.strip() if category_element else "Category not found"

        # Failsafe for size
        size_element = item.select_one('.stats img[alt="Size"]')
        size = size_element.parent.text.strip() if size_element and size_element.parent else "Size not found"

        # Failsafe for seeders
        seeders_element = item.select_one('.stats img[alt="Seeder"]')
        seeders = seeders_element.parent.text.strip() if seeders_element and seeders_element.parent else "Seeders not found"

        # Failsafe for leechers
        leechers_element = item.select_one('.stats img[alt="Leecher"]')
        leechers = leechers_element.parent.text.strip() if leechers_element and leechers_element.parent else "Leechers not found"

        # Failsafe for date
        date_element = item.select_one('.stats img[alt="Date"]')
        date = date_element.parent.text.strip() if date_element and date_element.parent else "Date not found"

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

        # Limit to the first 5 results
        if len(results) >= 5:
            break

    return results

@app.route('/torrents', methods=['GET'])
def torrents():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    results = scrape_website(query)
    return jsonify(results)

@app.route('/infoglobal', methods=['GET'])
def get_filtered_torrents():
    try:
        filters = {
            'filter': 'downloading',
            'sort': 'time_active',
            'limit': 10,
            'offset': 0
        }
        torrent_list = qb.torrents(**filters)
        if isinstance(torrent_list, list):
            return jsonify(torrent_list)
        else:
            return jsonify({"error": "Torrent list not available"}), 404
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": str(e)}), 404

if __name__ == '__main__':
    app.run(debug=True)
