# Stripe Testing Guide for Relex

This guide provides step-by-step instructions for setting up and testing Stripe integration with the Relex application. It covers creating test products and prices, setting up webhook forwarding, and testing subscription-related features.

## Overview

The Relex application uses Stripe for payment processing and subscription management. The following features rely on Stripe:

1. **One-time payments** for individual cases (Tier 1, 2, and 3)
2. **Subscription plans** for individuals and organizations
3. **Webhook handling** for processing Stripe events (checkout completion, subscription updates, etc.)
4. **Organization deletion restrictions** based on active subscriptions

## Prerequisites

- macOS with Homebrew installed
- A Stripe account with API access
- The Relex backend application running locally or deployed

## Setup Instructions

### 1. Install and Configure Stripe CLI

The Stripe CLI is a powerful tool for interacting with the Stripe API and testing webhooks locally.

```bash
# Navigate to the scripts directory
cd scripts/stripe

# Make the script executable (if not already)
chmod +x setup_stripe_cli.sh

# Run the script
./setup_stripe_cli.sh
```

This script will:
- Install the Stripe CLI using Homebrew (if not already installed)
- Log you in to your Stripe account (will open a browser window)
- Display the current configuration

### 2. Import Products and Prices

To test subscription features, you need to create products and prices in your Stripe account. The script will create the following:

**Products:**
- Individual case tiers (1, 2, and 3)
- Individual subscription plan
- Organization Basic plan (up to 5 members)
- Organization Pro plan (up to 20 members)

**Prices:**
- One-time payments for each case tier
- Monthly and annual subscriptions for individual plans
- Monthly and annual subscriptions for organization plans

```bash
# Make the script executable (if not already)
chmod +x import_products_prices.sh

# Run the script
./import_products_prices.sh
```

After running the script, verify that the products and prices appear in your [Stripe Dashboard](https://dashboard.stripe.com/test/products).

### 3. Set Up Webhook Forwarding

Stripe uses webhooks to notify your application about events (like successful payments or subscription updates). To test webhooks locally, you need to set up webhook forwarding.

```bash
# Make the script executable (if not already)
chmod +x setup_webhook.sh

# Run the script
./setup_webhook.sh
```

The script will prompt you to choose between:
1. Forwarding to a local development server (e.g., http://localhost:5001/webhooks/stripe)
2. Forwarding to a deployed Cloud Function (e.g., https://relex-api-gateway-dev-mvef5dk.ew.gateway.dev/webhooks/stripe)

**Important:** The script will display a webhook signing secret. You need to set this as the `STRIPE_WEBHOOK_SECRET` environment variable in your application.

### 4. Test Webhook Events

You can trigger test webhook events to simulate Stripe events without making actual payments.

```bash
# Make the script executable (if not already)
chmod +x test_webhook_events.sh

# Run the script
./test_webhook_events.sh
```

The script will display a menu of common webhook events to trigger, including:
- `checkout.session.completed` (for subscriptions and one-time payments)
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

## Testing Subscription Features

### Testing the Checkout Flow

1. Make sure your application is running (locally or deployed)
2. Set up webhook forwarding using `./setup_webhook.sh`
3. In your application, initiate a checkout session for a subscription:
   - Call the `/v1/payments/checkout` endpoint with appropriate parameters
   - Example payload for organization subscription:
     ```json
     {
       "mode": "subscription",
       "planId": "price_org_basic_monthly",
       "organizationId": "your-organization-id",
       "successUrl": "https://relex.ro/success",
       "cancelUrl": "https://relex.ro/cancel"
     }
     ```
4. Complete the checkout using a [Stripe test card](https://stripe.com/docs/testing#cards)
5. Verify that the webhook event is received and processed correctly:
   - Check your application logs
   - Verify that the organization's subscription status is updated in Firestore

### Testing Organization Deletion with Active Subscription

The Relex application prevents deleting organizations with active subscriptions. To test this feature:

1. Create an organization in your application
2. Purchase a subscription for the organization (using the checkout flow above)
3. Attempt to delete the organization by calling the delete endpoint
4. Verify that the deletion is blocked with an appropriate error message:
   ```json
   {
     "error": "Bad Request",
     "message": "Cannot delete organization with active subscription. Please cancel the subscription first."
   }
   ```
5. Cancel the subscription (using the `/v1/payments/cancel-subscription` endpoint)
6. Verify that the organization can now be deleted

## Troubleshooting

### Webhook Events Not Being Received

- Check that the webhook forwarding is running (`./setup_webhook.sh`)
- Verify that the webhook URL is correct
- Check your application logs for any errors processing the webhook
- Ensure the `STRIPE_WEBHOOK_SECRET` environment variable is set correctly in your application

### Products or Prices Not Appearing in Stripe Dashboard

- Check the output of the `import_products_prices.sh` script for any errors
- Verify that you're looking at the Test Mode dashboard in Stripe
- Try running the import script again with the corrected CSV files

## Additional Resources

- [Stripe CLI Documentation](https://stripe.com/docs/stripe-cli)
- [Stripe Testing Documentation](https://stripe.com/docs/testing)
- [Stripe Webhook Documentation](https://stripe.com/docs/webhooks)
- [Stripe Test Cards](https://stripe.com/docs/testing#cards)
