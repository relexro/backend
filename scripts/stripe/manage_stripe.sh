#!/bin/bash
# Comprehensive Stripe resource management script with centralized configuration

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/config.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

# Function to check if jq is available
check_jq() {
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed. Please install jq to use this script."
        print_status "On macOS: brew install jq"
        print_status "On Ubuntu/Debian: sudo apt-get install jq"
        exit 1
    fi
}

# Function to check if config file exists
check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        print_error "Configuration file not found: $CONFIG_FILE"
        exit 1
    fi
}

# Function to read config value
get_config() {
    local key=$1
    jq -r "$key" "$CONFIG_FILE"
}

# Function to get array from config
get_config_array() {
    local key=$1
    jq -r "$key[]" "$CONFIG_FILE"
}

# Function to get object keys
get_config_keys() {
    local key=$1
    jq -r "$key | keys[]" "$CONFIG_FILE"
}

# Function to get value from temporary file
get_temp_value() {
    local file=$1
    local key=$2
    grep "^$key=" "$file" | cut -d'=' -f2
}

# Function to show usage
show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  create                  Create all Stripe resources (uses config.json)"
    echo "  update                  Update existing Stripe resources (uses config.json)"
    echo "  delete                  Delete/deactivate all Stripe resources"
    echo "  list                    List all Stripe resources"
    echo "  clean                   Clean up old/inactive resources"
    echo "  config                  Show current configuration"
    echo "  validate                Validate configuration file"
    echo ""
    echo "Configuration:"
    echo "  Edit scripts/stripe/config.json to modify:"
    echo "  - Webhook URL and events"
    echo "  - Product names, descriptions, and pricing"
    echo "  - Coupon and promotion code details"
    echo "  - Tax rate information"
    echo ""
    echo "Examples:"
    echo "  $0 create"
    echo "  $0 update"
    echo "  $0 delete"
    echo "  $0 list"
    echo "  $0 config"
}

# Function to show current configuration
show_config() {
    print_header "Current Configuration"

    echo -e "\n${BLUE}Environment:${NC} $(get_config '.environment')"
    echo -e "${BLUE}Webhook URL:${NC} $(get_config '.webhook_url')"

    echo -e "\n${BLUE}Products:${NC}"
    for product_key in $(get_config_keys '.products'); do
        name=$(get_config ".products.$product_key.name")
        echo "  - $product_key: $name"
    done

    echo -e "\n${BLUE}Prices:${NC}"
    for price_key in $(get_config_keys '.prices'); do
        nickname=$(get_config ".prices.$price_key.nickname")
        amount=$(get_config ".prices.$price_key.unit_amount")
        currency=$(get_config ".prices.$price_key.currency")
        echo "  - $price_key: $nickname ($(($amount / 100)) $currency)"
    done

    echo -e "\n${BLUE}Webhook Events:${NC}"
    get_config_array '.webhook_events' | while read -r event; do
        echo "  - $event"
    done
}

# Function to validate configuration
validate_config() {
    print_header "Validating Configuration"

    # Check if config file is valid JSON
    if ! jq empty "$CONFIG_FILE" 2>/dev/null; then
        print_error "Configuration file is not valid JSON"
        return 1
    fi

    # Check required fields
    local required_fields=(".environment" ".webhook_url" ".products" ".prices")
    for field in "${required_fields[@]}"; do
        if [ "$(get_config "$field")" = "null" ]; then
            print_error "Required field missing: $field"
            return 1
        fi
    done

    print_status "Configuration is valid"
}

# Function to create all resources from config
create_resources() {
    print_header "Creating Stripe Resources from Configuration"

    local webhook_url=$(get_config '.webhook_url')
    local environment=$(get_config '.environment')

    print_status "Environment: $environment"
    print_status "Webhook URL: $webhook_url"

    # Store created resource IDs in temporary files
    PRODUCT_IDS_FILE=$(mktemp)
    PRICE_IDS_FILE=$(mktemp)
    COUPON_IDS_FILE=$(mktemp)

    # Create products
    print_status "Creating products..."
    for product_key in $(get_config_keys '.products'); do
        name=$(get_config ".products.$product_key.name")
        description=$(get_config ".products.$product_key.description")
        statement_descriptor=$(get_config ".products.$product_key.statement_descriptor")
        active=$(get_config ".products.$product_key.active")

        print_status "Creating product: $name"
        PRODUCT_ID=$(stripe products create \
            --name="$name" \
            --description="$description" \
            --statement-descriptor="$statement_descriptor" \
            --active=$active | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)

        echo "$product_key=$PRODUCT_ID" >> "$PRODUCT_IDS_FILE"
        print_status "Created product $product_key: $PRODUCT_ID"
    done

    # Create prices
    print_status "Creating prices..."
    for price_key in $(get_config_keys '.prices'); do
        product_key=$(get_config ".prices.$price_key.product")
        currency=$(get_config ".prices.$price_key.currency")
        unit_amount=$(get_config ".prices.$price_key.unit_amount")
        nickname=$(get_config ".prices.$price_key.nickname")
        lookup_key=$(get_config ".prices.$price_key.lookup_key")
        price_type=$(get_config ".prices.$price_key.type")

        # Add timestamp to lookup key to avoid conflicts
        unique_lookup_key="${lookup_key}_$(date +%s)"

        print_status "Creating price: $nickname"

        PRODUCT_ID=$(get_temp_value "$PRODUCT_IDS_FILE" "$product_key")

        if [ "$price_type" = "recurring" ]; then
            recurring_interval=$(get_config ".prices.$price_key.recurring_interval")
            PRICE_ID=$(stripe prices create \
                --product=$PRODUCT_ID \
                --currency=$currency \
                --unit-amount=$unit_amount \
                --recurring.interval=$recurring_interval \
                --nickname="$nickname" \
                --lookup-key="$unique_lookup_key" | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)
        else
            PRICE_ID=$(stripe prices create \
                --product=$PRODUCT_ID \
                --currency=$currency \
                --unit-amount=$unit_amount \
                --nickname="$nickname" \
                --lookup-key="$unique_lookup_key" | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)
        fi

        echo "$price_key=$PRICE_ID" >> "$PRICE_IDS_FILE"
        print_status "Created price $price_key: $PRICE_ID"
    done

    # Create coupons
    print_status "Creating coupons..."
    for coupon_key in $(get_config_keys '.coupons'); do
        name=$(get_config ".coupons.$coupon_key.name")
        percent_off=$(get_config ".coupons.$coupon_key.percent_off")
        duration=$(get_config ".coupons.$coupon_key.duration")

        print_status "Creating coupon: $name"
        COUPON_ID=$(stripe coupons create \
            --name="$name" \
            --duration=$duration \
            -d "percent_off=$percent_off" | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)

        echo "$coupon_key=$COUPON_ID" >> "$COUPON_IDS_FILE"
        print_status "Created coupon $coupon_key: $COUPON_ID"
    done

    # Create promotion codes
    print_status "Creating promotion codes..."
    for promo_key in $(get_config_keys '.promotion_codes'); do
        coupon_key=$(get_config ".promotion_codes.$promo_key.coupon")
        code=$(get_config ".promotion_codes.$promo_key.code")
        active=$(get_config ".promotion_codes.$promo_key.active")

        # Add timestamp to code to avoid conflicts
        unique_code="${code}_$(date +%s)"

        COUPON_ID=$(get_temp_value "$COUPON_IDS_FILE" "$coupon_key")

        print_status "Creating promotion code: $unique_code"
        PROMO_ID=$(stripe promotion_codes create \
            --coupon=$COUPON_ID \
            --code=$unique_code \
            --active=$active | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)

        print_status "Created promotion code $promo_key: $PROMO_ID"
    done

    # Create tax rates
    print_status "Creating tax rates..."
    for tax_key in $(get_config_keys '.tax_rates'); do
        display_name=$(get_config ".tax_rates.$tax_key.display_name")
        description=$(get_config ".tax_rates.$tax_key.description")
        jurisdiction=$(get_config ".tax_rates.$tax_key.jurisdiction")
        percentage=$(get_config ".tax_rates.$tax_key.percentage")
        inclusive=$(get_config ".tax_rates.$tax_key.inclusive")
        active=$(get_config ".tax_rates.$tax_key.active")

        print_status "Creating tax rate: $display_name"
        TAX_ID=$(stripe tax_rates create \
            --display-name="$display_name" \
            --description="$description" \
            --jurisdiction=$jurisdiction \
            --inclusive=$inclusive \
            --active=$active \
            -d "percentage=$percentage" | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)

        print_status "Created tax rate $tax_key: $TAX_ID"
    done

    # Create webhook endpoint
    print_status "Creating webhook endpoint..."
    webhook_events=""
    for event in $(get_config_array '.webhook_events'); do
        webhook_events="$webhook_events --enabled-events=$event"
    done

    WEBHOOK_RESULT=$(stripe webhook_endpoints create \
        --url=$webhook_url \
        $webhook_events \
        --description="Relex Application Webhook ($environment)")

    WEBHOOK_ID=$(echo "$WEBHOOK_RESULT" | grep -o '"id": "[^"]*' | head -1 | cut -d'"' -f4)
    WEBHOOK_SECRET=$(echo "$WEBHOOK_RESULT" | grep -o '"secret": "[^"]*' | head -1 | cut -d'"' -f4)
    print_status "Created Webhook Endpoint: $WEBHOOK_ID"

    # Store webhook secret in Secret Manager
    print_status "Storing webhook secret in Secret Manager..."
    echo -n $WEBHOOK_SECRET | gcloud secrets versions add stripe-webhook-secret --data-file=-

    print_header "Resource Creation Complete"
    print_status "All Stripe resources have been created successfully!"
    print_status "Webhook secret has been stored in Google Cloud Secret Manager."

    # Clean up temporary files
    rm -f "$PRODUCT_IDS_FILE" "$PRICE_IDS_FILE" "$COUPON_IDS_FILE"
}

# Function to delete/deactivate resources (same as before)
delete_resources() {
    print_header "Deleting/Deactivating Stripe Resources"

    print_warning "This will deactivate/delete all Stripe resources. Continue? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        print_status "Operation cancelled."
        return
    fi

    # Delete webhook endpoints
    print_status "Deleting webhook endpoints..."
    stripe webhook_endpoints list --limit=10 | grep -o "we_[a-zA-Z0-9]*" | while read -r ID; do
        print_status "Deleting webhook endpoint: $ID"
        stripe webhook_endpoints delete $ID || true
    done

    # Deactivate promotion codes
    print_status "Deactivating promotion codes..."
    stripe promotion_codes list --limit=10 | grep -o "promo_[a-zA-Z0-9]*" | while read -r ID; do
        print_status "Deactivating promotion code: $ID"
        stripe promotion_codes update $ID --active=false || true
    done

    # Delete coupons
    print_status "Deleting coupons..."
    stripe coupons list --limit=10 | grep -o '"id": "[^"]*' | cut -d'"' -f4 | while read -r ID; do
        print_status "Deleting coupon: $ID"
        stripe coupons delete $ID || true
    done

    # Deactivate prices
    print_status "Deactivating prices..."
    stripe prices list --limit=50 | grep -o "price_[a-zA-Z0-9]*" | while read -r ID; do
        print_status "Deactivating price: $ID"
        stripe prices update $ID --active=false || true
    done

    # Deactivate products
    print_status "Deactivating products..."
    stripe products list --limit=20 | grep -o "prod_[a-zA-Z0-9]*" | while read -r ID; do
        print_status "Deactivating product: $ID"
        stripe products update $ID --active=false || true
    done

    # Deactivate tax rates
    print_status "Deactivating tax rates..."
    stripe tax_rates list --limit=10 | grep -o "txr_[a-zA-Z0-9]*" | while read -r ID; do
        print_status "Deactivating tax rate: $ID"
        stripe tax_rates update $ID --active=false || true
    done

    print_header "Resource Deletion/Deactivation Complete"
}

# Function to list resources
list_resources() {
    print_header "Stripe Resources"

    echo -e "\n${BLUE}Products:${NC}"
    stripe products list --limit=20

    echo -e "\n${BLUE}Prices:${NC}"
    stripe prices list --limit=50

    echo -e "\n${BLUE}Webhook Endpoints:${NC}"
    stripe webhook_endpoints list --limit=10

    echo -e "\n${BLUE}Coupons:${NC}"
    stripe coupons list --limit=10

    echo -e "\n${BLUE}Promotion Codes:${NC}"
    stripe promotion_codes list --limit=10

    echo -e "\n${BLUE}Tax Rates:${NC}"
    stripe tax_rates list --limit=10
}

# Main script logic
check_jq
check_config

case "$1" in
    create)
        validate_config
        create_resources
        ;;
    update)
        validate_config
        print_status "Update functionality will be implemented based on specific needs"
        ;;
    delete)
        delete_resources
        ;;
    list)
        list_resources
        ;;
    clean)
        print_status "Clean functionality will remove inactive resources"
        delete_resources
        ;;
    config)
        show_config
        ;;
    validate)
        validate_config
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
