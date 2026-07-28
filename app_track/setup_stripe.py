import stripe
import sys
import os

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "sk_test_dummy_placeholder_key")

try:
    starter_prod = stripe.Product.create(name="Starter Plan")
    starter_price = stripe.Price.create(
      unit_amount=9900,
      currency="usd",
      recurring={"interval": "month"},
      product=starter_prod.id,
    )
    
    growth_prod = stripe.Product.create(name="Growth Plan")
    growth_price = stripe.Price.create(
      unit_amount=29900,
      currency="usd",
      recurring={"interval": "month"},
      product=growth_prod.id,
    )
    
    enterprise_prod = stripe.Product.create(name="Enterprise Plan")
    enterprise_price = stripe.Price.create(
      unit_amount=99900,
      currency="usd",
      recurring={"interval": "month"},
      product=enterprise_prod.id,
    )
    
    print(f"STRIPE_PRICE_STARTER='{starter_price.id}'")
    print(f"STRIPE_PRICE_GROWTH='{growth_price.id}'")
    print(f"STRIPE_PRICE_ENTERPRISE='{enterprise_price.id}'")
except Exception as e:
    print(e)
