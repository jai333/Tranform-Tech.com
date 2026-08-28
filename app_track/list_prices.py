import stripe
import os
from dotenv import load_dotenv

load_dotenv()
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
stripe.verify_ssl_certs = False

try:
    prices = stripe.Price.list(limit=10)
    for p in prices.data:
        print(f"Price ID: {p.id}, Product: {p.product}, Unit Amount: {p.unit_amount}")
except Exception as e:
    print("ERROR", str(e))
