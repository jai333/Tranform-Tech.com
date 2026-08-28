from tracking_app.gmaps_scraper import scrape_google_maps
print(list(scrape_google_maps('plumber', 'seattle', max_results=2)))
