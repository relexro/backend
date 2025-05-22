# Stripe Resource Management

This directory contains scripts for managing Stripe resources with centralized configuration.

## Files

- `manage_stripe.sh` - Main management script
- `config.json` - Centralized configuration file
- `README.md` - This documentation

## Quick Start

### 1. View Current Configuration
```bash
../terraform/scripts/stripe/manage_stripe.sh config
```

### 2. Edit Configuration
Edit `scripts/stripe/config.json` to modify:
- Product names, descriptions, and statement descriptors
- Pricing (amounts are in cents, e.g., 900 = €9.00)
- Webhook URL and events
- Coupon and promotion code details
- Tax rate information

### 3. Create All Resources
```bash
../terraform/scripts/stripe/manage_stripe.sh create
```

### 4. List All Resources
```bash
../terraform/scripts/stripe/manage_stripe.sh list
```

### 5. Delete All Resources
```bash
../terraform/scripts/stripe/manage_stripe.sh delete
```

## Configuration Examples

### Changing Prices
To change the individual monthly price from €9 to €12:
```json
{
  "prices": {
    "individual_monthly": {
      "unit_amount": 1200,
      "nickname": "Individual Monthly",
      ...
    }
  }
}
```

### Adding a New Product
```json
{
  "products": {
    "new_product": {
      "name": "New Product Name",
      "description": "Product description",
      "statement_descriptor": "STATEMENT DESC",
      "active": true
    }
  }
}
```

### Adding Prices for New Product
```json
{
  "prices": {
    "new_product_monthly": {
      "product": "new_product",
      "currency": "eur",
      "unit_amount": 1500,
      "nickname": "New Product Monthly",
      "lookup_key": "price_new_product_monthly",
      "type": "recurring",
      "recurring_interval": "month"
    }
  }
}
```

### Changing Webhook URL
```json
{
  "webhook_url": "https://your-new-domain.com/v1/webhooks/stripe"
}
```

## Commands

| Command | Description |
|---------|-------------|
| `create` | Create all Stripe resources from config |
| `update` | Update existing resources (planned) |
| `delete` | Delete/deactivate all resources |
| `list` | List all current resources |
| `config` | Show current configuration |
| `validate` | Validate configuration file |
| `clean` | Clean up inactive resources |

## Important Notes

1. **Pricing**: All amounts are in cents (e.g., 900 = €9.00)
2. **Unique Keys**: Lookup keys and promotion codes get timestamps appended to avoid conflicts
3. **Webhook Secret**: Automatically stored in Google Cloud Secret Manager
4. **Validation**: Configuration is validated before creating resources
5. **Cleanup**: Temporary files are automatically cleaned up

## Configuration Structure

```json
{
  "environment": "dev",
  "webhook_url": "https://your-api-gateway.com/webhooks/stripe",
  "webhook_events": ["event1", "event2"],
  "products": {
    "product_key": {
      "name": "Product Name",
      "description": "Description",
      "statement_descriptor": "STATEMENT",
      "active": true
    }
  },
  "prices": {
    "price_key": {
      "product": "product_key",
      "currency": "eur",
      "unit_amount": 900,
      "nickname": "Display Name",
      "lookup_key": "lookup_key",
      "type": "one_time|recurring",
      "recurring_interval": "month|year"
    }
  },
  "coupons": {
    "coupon_key": {
      "name": "Coupon Name",
      "percent_off": 25,
      "duration": "once|repeating|forever"
    }
  },
  "promotion_codes": {
    "promo_key": {
      "coupon": "coupon_key",
      "code": "PROMOCODE",
      "active": true
    }
  },
  "tax_rates": {
    "tax_key": {
      "display_name": "Tax Name",
      "description": "Tax Description",
      "jurisdiction": "DE",
      "percentage": 19,
      "inclusive": false,
      "active": true
    }
  }
}
```

## Workflow

1. **Edit** `config.json` with your desired changes
2. **Validate** configuration: `./manage_stripe.sh validate`
3. **Preview** configuration: `./manage_stripe.sh config`
4. **Create** resources: `./manage_stripe.sh create`
5. **Verify** resources: `./manage_stripe.sh list`

## Error Handling

- Configuration validation prevents invalid JSON
- Required fields are checked before creation
- Stripe CLI errors are displayed with context
- Temporary files are cleaned up automatically
- Failed operations don't affect existing resources
