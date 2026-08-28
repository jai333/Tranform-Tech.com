import stripe
import os
from dotenv import load_dotenv
load_dotenv()
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
try:
    session = stripe.checkout.Session.create(customer_email='test@example.com', line_items=[{'price': os.environ.get('STRIPE_PRICE_GROWTH'), 'quantity': 1}], mode='subscription', success_url='http://localhost:8000/success', cancel_url='http://localhost:8000/cancel')
    print('SUCCESS', session.url)
except Exception as e:
    print('ERROR', str(e))
