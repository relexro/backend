# Payments and Subscription System

## Overview

Relex implements a flexible payment and subscription system to monetize the AI legal assistant. The system supports both individual user payments and organization subscriptions, with different tiers of service based on case complexity.

## Case Tier System

Cases are classified into three tiers based on their complexity:

1. **Case Tier 1**: Simple cases requiring minimal AI interaction
   - Examples: Basic legal information requests, simple document generation
   - Lower quota consumption
   - Minimal features required

2. **Case Tier 2**: Moderate complexity cases
   - Examples: Standard legal documents, basic legal research
   - Medium quota consumption
   - Standard feature set

3. **Case Tier 3**: Complex cases requiring extensive AI interaction
   - Examples: Complex litigation, detailed legal analysis, multi-party cases
   - Higher quota consumption
   - Full feature set

The tier of a case is determined by the AI during the initial interaction with the user, based on the case description and requirements.

## Quota System

The system uses a quota mechanism to control and monetize usage:

1. **Quota Definition**:
   - Each user or organization has a quota allocation
   - Quota is consumed based on case tier (Tier 3 > Tier 2 > Tier 1)
   - Quota may be replenished through subscriptions or one-time purchases

2. **Quota Checks**:
   - The `check_quota` tool verifies available quota before processing a case
   - If insufficient quota is available, the agent informs the user of payment requirements

3. **Quota Management**:
   - Quota is tracked in the user or organization document in Firestore
   - Subscription events trigger quota updates
   - Administrators can view quota usage in the dashboard

## Subscription Models

### Individual Subscriptions

For individual users:

1. **Free Tier**:
   - Limited quota for Case Tier 1 only
   - Basic features
   - No recurring payment

2. **Basic Subscription**:
   - Moderate quota for Case Tier 1 and 2
   - Standard features
   - Monthly or annual payment

3. **Premium Subscription**:
   - Higher quota for all Case Tiers (1, 2, and 3)
   - All features
   - Monthly or annual payment

### Organization Subscriptions

For law firms and organizations:

1. **Startup**:
   - Moderate quota shared across organization members
   - Access to Case Tier 1 and 2
   - Up to 5 members

2. **Professional**:
   - Higher quota shared across organization members
   - Access to all Case Tiers
   - Up to 20 members

3. **Enterprise**:
   - Custom quota allocation
   - Access to all Case Tiers
   - Unlimited members
   - Custom features and support

## Payment Processing with Stripe

The system integrates with Stripe for payment processing:

1. **Stripe Resources**:
   - **Products**: Represent subscription types and one-time purchases
   - **Prices**: Define specific price points for products
   - **Customers**: Map to Relex users and organizations
   - **Subscriptions**: Track recurring payment arrangements
   - **Payment Intents**: Handle one-time payments
   - **Invoices**: Record billing history

2. **Integration Points**:
   - Client-side Stripe.js for secure payment collection
   - Stripe API for subscription management
   - Stripe Connect for potential marketplace features (future)

## Payment Flows

### Subscription Flow

1. User selects a subscription plan
2. System creates a Stripe Checkout session
3. User completes payment on Stripe-hosted page
4. Stripe webhook notifies the backend of successful payment
5. Backend updates user/organization quota and subscription status
6. User can immediately access the subscribed features

### Case-Based Payment Flow

1. User starts a new case
2. AI determines the case tier
3. System checks available quota
4. If quota is insufficient:
   - System creates a payment intent
   - User is prompted to pay
   - Upon successful payment, quota is updated
   - Case processing continues
5. If quota is sufficient:
   - Case processing continues immediately

## Implementation

### Key Files

- `functions/src/payments.py`: Main payment processing logic
- `functions/src/cases.py`: Case tier determination and quota checks
- `functions/src/organization.py`: Organization subscription management
- `functions/src/user.py`: User subscription management

### Key Functions

1. **`create_checkout_session`**: Creates a Stripe Checkout session for subscription purchases
2. **`create_payment_intent`**: Creates a Stripe Payment Intent for one-time purchases
3. **`handle_stripe_webhook`**: Processes Stripe webhook events
4. **`check_quota`**: Verifies if a user/organization has sufficient quota
5. **`update_quota`**: Updates quota based on payments and usage

### Stripe Webhook Handling

The system handles various Stripe webhook events:

1. **`checkout.session.completed`**: When a subscription purchase is completed
2. **`payment_intent.succeeded`**: When a one-time payment succeeds
3. **`customer.subscription.updated`**: When a subscription is updated
4. **`customer.subscription.deleted`**: When a subscription is canceled
5. **`invoice.payment_succeeded`**: When a recurring payment succeeds
6. **`invoice.payment_failed`**: When a recurring payment fails

Each event type triggers appropriate updates to the user/organization status and quota in Firestore.

## Firestore Schema

### User Subscription Data

```
users/{userId}
  |- subscription: {
  |    subscription_id: "sub_123456",
  |    status: "active",
  |    plan: "premium",
  |    current_period_end: "2023-12-31T23:59:59Z",
  |    cancel_at_period_end: false,
  |    stripe_customer_id: "cus_123456"
  |  }
  |- quota: {
  |    tier_1: {
  |      remaining: 10,
  |      total: 20,
  |      reset_date: "2023-12-31T23:59:59Z"
  |    },
  |    tier_2: {
  |      remaining: 5,
  |      total: 10,
  |      reset_date: "2023-12-31T23:59:59Z"
  |    },
  |    tier_3: {
  |      remaining: 2,
  |      total: 5,
  |      reset_date: "2023-12-31T23:59:59Z"
  |    }
  |  }
```

### Organization Subscription Data

```
organizations/{organizationId}
  |- subscription: {
  |    subscription_id: "sub_123456",
  |    status: "active",
  |    plan: "professional",
  |    current_period_end: "2023-12-31T23:59:59Z",
  |    cancel_at_period_end: false,
  |    stripe_customer_id: "cus_123456"
  |  }
  |- quota: {
  |    tier_1: {
  |      remaining: 50,
  |      total: 100,
  |      reset_date: "2023-12-31T23:59:59Z"
  |    },
  |    tier_2: {
  |      remaining: 25,
  |      total: 50,
  |      reset_date: "2023-12-31T23:59:59Z"
  |    },
  |    tier_3: {
  |      remaining: 10,
  |      total: 20,
  |      reset_date: "2023-12-31T23:59:59Z"
  |    }
  |  }
```

## API Endpoints

The system exposes several API endpoints for payment management:

1. **Create Checkout Session**: 
   ```
   POST /subscriptions/checkout
   ```

2. **Get Subscription Status**: 
   ```
   GET /users/me/subscription
   ```

3. **Cancel Subscription**: 
   ```
   POST /users/me/subscription/cancel
   ```

4. **Create Payment Intent for Case**: 
   ```
   POST /cases/{caseId}/payment
   ```

5. **Stripe Webhook Endpoint**: 
   ```
   POST /webhooks/stripe
   ```

## Security Considerations

1. **Webhook Verification**: All Stripe webhooks are verified using the webhook secret
2. **User Authentication**: All payment endpoints require authentication
3. **Quota Validation**: The system validates quota before allowing case processing
4. **Subscription Verification**: The backend verifies subscription status with Stripe

## Future Enhancements

1. **Metered Billing**: More granular usage-based billing
2. **Promotional Codes**: Support for discount codes and promotions
3. **Enhanced Analytics**: Detailed analytics for payment and usage patterns
4. **Multi-Currency Support**: Support for multiple currencies
5. **Tax Management**: Integration with tax calculation services 