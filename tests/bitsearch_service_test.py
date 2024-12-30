import unittest
import requests

class HttpIssueTestCase(unittest.TestCase):
    def test_url_status(self):
        print("Testing simple URL for HTTP issues...")
        url = "https://bitsearch.to/search?q=pulp+fiction&category=1&subcat=2"

        try:
            response = requests.get(url)
            self.assertEqual(response.status_code, 200, f"URL returned {response.status_code} instead of 200.")
        except requests.RequestException as e:
            self.fail(f"HTTP request failed with exception: {e}")

if __name__ == '__main__':
    unittest.main()
