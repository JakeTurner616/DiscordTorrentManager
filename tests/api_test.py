import sys
import os
import time
import unittest
from threading import Thread

# Add the parent directory to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, scrape_website  # Now it correctly imports from the parent directory

class FlaskAppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start the Flask server in a separate thread
        cls.server_thread = Thread(target=app.run, kwargs={'debug': False, 'use_reloader': False})
        cls.server_thread.start()
        # Give the server a second to ensure it starts
        time.sleep(1)

    @classmethod
    def tearDownClass(cls):
        # Terminate the server thread
        os._exit(0)

    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.testing = True

    def test_scrape_website(self):
        print("starting test. this should take less than 10 seconds.")
        query = "pulp fiction"
        results = scrape_website(query)
        
        expected_keys = {
            'title': '.title a',
            'link': '.title a',
            'category': '.category',
            'size': '.stats img[alt="Size"]',
            'seeders': '.stats img[alt="Seeder"]',
            'leechers': '.stats img[alt="Leecher"]',
            'date': '.stats img[alt="Date"]',
            'magnet_link': '.dl-magnet'
        }
        
        # Ensure the result is a list
        self.assertIsInstance(results, list)
        
        failed_data_points = []

        for result in results:
            for key, selector in expected_keys.items():
                if key not in result or result[key].endswith("not found"):
                    failed_data_points.append((key, selector, result[key]))

        if failed_data_points:
            print("Test Failed. The following data points were not collected correctly:")
            for key, selector, value in failed_data_points:
                print(f"Data point: {key}, Selector: {selector}, Value: {value}")
            self.fail("Some data points were not collected correctly.")
        else:
            print("Test Passed. All data points were collected correctly.")

if __name__ == '__main__':
    unittest.main()
