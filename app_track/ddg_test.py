import urllib.request
import urllib.parse
import ssl
from html.parser import HTMLParser

class DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_item = {}
        self.in_title = False
        self.in_snippet = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'a' and 'class' in d and 'result__snippet' in d['class']:
            self.current_item = {'url': d.get('href')}
            self.in_snippet = True
        elif tag == 'h2' and 'class' in d and 'result__title' in d['class']:
            self.in_title = True

    def handle_endtag(self, tag):
        if tag == 'a' and self.in_snippet:
            self.in_snippet = False
            if 'url' in self.current_item:
                self.results.append(self.current_item)
                self.current_item = {}
        elif tag == 'h2' and self.in_title:
            self.in_title = False

    def handle_data(self, data):
        if self.in_title and 'url' in self.current_item:
            self.current_item['title'] = data.strip()
        elif self.in_snippet and 'url' in self.current_item:
            self.current_item['snippet'] = self.current_item.get('snippet', '') + data.strip()

ssl._create_default_https_context = ssl._create_unverified_context
query = 'site:linkedin.com/in/ "Python Developer"'
url = f'https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')

parser = DDGParser()
parser.feed(html)
print(parser.results)
