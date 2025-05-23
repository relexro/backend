#!/bin/bash
# WARNING: THIS SCRIPT IS HIGHLY DESTRUCTIVE AND WILL ATTEMPT TO DELETE
# ALL POSSIBLE RESOURCES FROM YOUR STRIPE ACCOUNT.
# IT IS INTENDED FOR SANDBOX/TEST ENVIRONMENTS ONLY.
# NO CONFIRMATION WILL BE ASKED. RUNNING THIS SCRIPT WILL IMMEDIATELY
# START THE DELETION PROCESS.
# USE WITH EXTREME CAUTION. THERE IS NO UNDO.

set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration & Helpers ---
STRIPE_API_KEY="${STRIPE_SECRET_KEY}" # Use the standard environment variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

_print_colored_stderr() {
    local color="$1"
    local prefix="$2"
    local message="$3"
    echo -e "${color}${prefix}${NC} ${message}" >&2
}

print_status_stderr() {
    _print_colored_stderr "$GREEN" "[INFO]" "$1"
}

print_warning_stderr() {
    _print_colored_stderr "$YELLOW" "[WARNING]" "$1"
}

print_error_stderr() {
    _print_colored_stderr "$RED" "[ERROR]" "$1"
}

print_header_stderr() {
    echo -e "\n${BLUE}=== $1 ===${NC}\n" >&2
}

check_dependencies() {
    print_header_stderr "Performing Pre-run Checks"
    if ! command -v stripe &> /dev/null; then
        print_error_stderr "Stripe CLI is required but not installed. Please install it first."
        exit 1
    fi
    if ! command -v jq &> /dev/null; then
        print_error_stderr "jq is required but not installed. Please install it first."
        exit 1
    fi
    if [ -z "$STRIPE_API_KEY" ]; then
        print_error_stderr "STRIPE_SECRET_KEY environment variable is not set. Please set it to your test mode secret key."
        exit 1
    fi
    if [[ "$STRIPE_API_KEY" != sk_test_* ]]; then
        print_error_stderr "The STRIPE_SECRET_KEY does not appear to be a test key (sk_test_...). This script is too dangerous for live keys."
        print_error_stderr "SCRIPT WILL NOT RUN."
        exit 1
    fi
    print_status_stderr "STRIPE_SECRET_KEY is a test key: $STRIPE_API_KEY"
    print_status_stderr "Dependencies look OK."
    print_warning_stderr "Proceeding with highly destructive operations immediately as no confirmation is required for this script version."
}

# --- Deletion Functions ---

delete_all_subscriptions() {
    print_header_stderr "Canceling and Deleting Subscriptions"
    local sub_ids
    sub_ids=$(stripe subscriptions list --status=all --limit=100 --api-key "$STRIPE_API_KEY" | jq -r '.data[].id // empty')
    if [ -z "$sub_ids" ]; then
        print_status_stderr "No subscriptions found to delete."
        return
    fi
    for id in $sub_ids; do
        print_status_stderr "Attempting to cancel subscription: $id"
        # Check for and release subscription schedules first
        local schedule_id
        schedule_id=$(stripe subscription_schedules list --subscription "$id" --api-key "$STRIPE_API_KEY" | jq -r '.data[0].id // empty')
        if [ -n "$schedule_id" ]; then
            print_status_stderr "Subscription $id has a schedule $schedule_id. Releasing schedule..."
            stripe subscription_schedules release "$schedule_id" --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to release schedule for $id. Cancellation might fail or behave unexpectedly."
        fi
        # `stripe subscriptions cancel` attempts to delete the subscription object by default
        stripe subscriptions cancel "$id" --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to cancel/delete subscription $id. It might have already been canceled or have other issues."
    done
    print_status_stderr "All found subscriptions processed for cancellation/deletion."
}

delete_all_promotion_codes() {
    print_header_stderr "Deactivating Promotion Codes"
    local promo_ids
    promo_ids=$(stripe promotion_codes list --active=true --limit=100 --api-key "$STRIPE_API_KEY" | jq -r '.data[].id // empty')
    if [ -z "$promo_ids" ]; then
        print_status_stderr "No active promotion codes found to deactivate."
    else
        for id in $promo_ids; do
            print_status_stderr "Deactivating promotion code: $id"
            stripe promotion_codes update "$id" --active=false --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to deactivate promotion code $id."
        done
    fi
    # Stripe CLI does not have a direct 'promotion_codes delete' command.
    print_status_stderr "Active promotion codes processed for deactivation."
}

delete_all_coupons() {
    print_header_stderr "Deleting Coupons"
    local coupon_ids
    coupon_ids=$(stripe coupons list --limit=100 --api-key "$STRIPE_API_KEY" | jq -r '.data[].id // empty')
     if [ -z "$coupon_ids" ]; then
        print_status_stderr "No coupons found to delete."
        return
    fi
    for id in $coupon_ids; do
        print_status_stderr "Deleting coupon: $id"
        stripe coupons delete "$id" --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to delete coupon $id."
    done
    print_status_stderr "All found coupons processed for deletion."
}

delete_all_prices() {
    print_header_stderr "Deactivating All Active Prices"
    local starting_after=""
    local batch_count=0
    local total_deactivated=0

    while true; do
        batch_count=$((batch_count + 1))
        print_status_stderr "Fetching batch $batch_count of active prices..."
        local list_args="--active=true --limit=100"
        if [ -n "$starting_after" ]; then
            list_args="$list_args --starting-after=$starting_after"
        fi
        local price_batch_data=$(stripe prices list $list_args --api-key "$STRIPE_API_KEY")
        local price_ids_batch=$(echo "$price_batch_data" | jq -r '.data[].id // empty')

        if [ -z "$price_ids_batch" ]; then
            if [ "$batch_count" -eq 1 ]; then
                print_status_stderr "No active prices found to deactivate."
            else
                print_status_stderr "No more active prices in this batch. All fetched."
            fi
            break
        fi

        for id in $price_ids_batch; do
            total_deactivated=$((total_deactivated + 1))
            print_status_stderr "Deactivating price $total_deactivated: $id"
            stripe prices update "$id" --active=false --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to deactivate price $id."
            starting_after="$id"
        done

        local has_more=$(echo "$price_batch_data" | jq -r '.has_more // false')
        if [ "$has_more" != "true" ]; then
            print_status_stderr "No more active prices (has_more is false)."
            break
        fi
    done

    print_status_stderr "All found active prices ($total_deactivated) processed for deactivation."
}

delete_all_products() {
    print_header_stderr "Deactivating and Deleting Products"
    # First, deactivate all active products
    print_status_stderr "Deactivating all active products..."
    local starting_after=""
    local batch_count=0
    local total_deactivated=0

    while true; do
        batch_count=$((batch_count + 1))
        print_status_stderr "Fetching batch $batch_count of active products..."
        local list_args="--active=true --limit=100"
        if [ -n "$starting_after" ]; then
            list_args="$list_args --starting-after=$starting_after"
        fi
        local product_batch_data=$(stripe products list $list_args --api-key "$STRIPE_API_KEY")
        local product_ids_batch=$(echo "$product_batch_data" | jq -r '.data[].id // empty')

        if [ -z "$product_ids_batch" ]; then
            if [ "$batch_count" -eq 1 ]; then
                print_status_stderr "No active products found to deactivate."
            else
                print_status_stderr "No more active products in this batch. All fetched."
            fi
            break
        fi

        for id in $product_ids_batch; do
            total_deactivated=$((total_deactivated + 1))
            print_status_stderr "Deactivating product $total_deactivated: $id"
            stripe products update "$id" --active=false --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to deactivate product $id."
            starting_after="$id"
        done

        local has_more=$(echo "$product_batch_data" | jq -r '.has_more // false')
        if [ "$has_more" != "true" ]; then
            print_status_stderr "No more active products (has_more is false)."
            break
        fi
    done

    print_status_stderr "All found active products ($total_deactivated) processed for deactivation."

    # Then, attempt to delete all products
    print_status_stderr "Attempting to delete all products..."
    starting_after=""
    batch_count=0
    local total_attempted=0
    local failed_deletions=0

    while true; do
        batch_count=$((batch_count + 1))
        print_status_stderr "Fetching batch $batch_count of products to delete..."
        local list_args="--limit=100"
        if [ -n "$starting_after" ]; then
            list_args="$list_args --starting-after=$starting_after"
        fi
        local product_batch_data=$(stripe products list $list_args --api-key "$STRIPE_API_KEY")
        local product_ids_batch=$(echo "$product_batch_data" | jq -r '.data[].id // empty')

        if [ -z "$product_ids_batch" ]; then
            if [ "$batch_count" -eq 1 ]; then
                print_status_stderr "No products found to delete."
            else
                print_status_stderr "No more products in this batch. All fetched."
            fi
            break
        fi

        for id in $product_ids_batch; do
            total_attempted=$((total_attempted + 1))
            print_status_stderr "Attempting to delete product $total_attempted: $id"
            if ! stripe products delete "$id" --api-key "$STRIPE_API_KEY"; then
                print_warning_stderr "Failed to delete product $id. It might have non-archived prices or other dependencies."
                failed_deletions=$((failed_deletions + 1))
            fi
            starting_after="$id"
        done

        local has_more=$(echo "$product_batch_data" | jq -r '.has_more // false')
        if [ "$has_more" != "true" ]; then
            print_status_stderr "No more products (has_more is false)."
            break
        fi
    done

    print_status_stderr "All found products ($total_attempted) processed for deletion."
    if [ "$failed_deletions" -gt 0 ]; then
        print_warning_stderr "$failed_deletions product(s) could not be deleted due to dependencies."
    fi
}

delete_all_tax_rates() {
    print_header_stderr "Deactivating Tax Rates"
    # Stripe API often prevents deletion of tax rates that have been used. Deactivation is the primary action.
    local tax_rate_ids
    tax_rate_ids=$(stripe tax_rates list --active=true --limit=100 --api-key "$STRIPE_API_KEY" | jq -r '.data[].id // empty')
    if [ -z "$tax_rate_ids" ]; then
        print_status_stderr "No active tax rates found to deactivate."
        return
    fi
    for id in $tax_rate_ids; do
        print_status_stderr "Deactivating tax rate: $id"
        stripe tax_rates update "$id" --active=false --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to deactivate tax rate $id."
    done
    print_status_stderr "All found active tax rates processed for deactivation."
}

delete_all_webhook_endpoints() {
    print_header_stderr "Deleting Webhook Endpoints"
    local webhook_ids
    webhook_ids=$(stripe webhook_endpoints list --limit=100 --api-key "$STRIPE_API_KEY" | jq -r '.data[].id // empty')
    if [ -z "$webhook_ids" ]; then
        print_status_stderr "No webhook endpoints found to delete."
        return
    fi
    for id in $webhook_ids; do
        print_status_stderr "Deleting webhook endpoint: $id"
        stripe webhook_endpoints delete "$id" --api-key "$STRIPE_API_KEY" || print_warning_stderr "Failed to delete webhook endpoint $id."
    done
    print_status_stderr "All found webhook endpoints processed for deletion."
}

delete_all_customers() {
    print_header_stderr "Deleting Customers"
    local customer_ids
    # Loop to fetch customers in batches until no more are returned
    local starting_after=""
    local batch_count=0
    local total_processed=0
    local failed_deletions=0

    print_status_stderr "Fetching and deleting customers in batches..."
    while true; do
        batch_count=$((batch_count + 1))
        print_status_stderr "Fetching batch $batch_count..."
        local list_args="--limit=100"
        if [ -n "$starting_after" ]; then
            list_args="$list_args --starting-after=$starting_after"
        fi
        
        customer_batch_data=$(stripe customers list $list_args --api-key "$STRIPE_API_KEY")
        customer_ids_batch=$(echo "$customer_batch_data" | jq -r '.data[].id // empty')

        if [ -z "$customer_ids_batch" ]; then
            if [ "$batch_count" -eq 1 ]; then # No customers found at all
                 print_status_stderr "No customers found to delete."
            else # No more customers in subsequent batches
                 print_status_stderr "No more customers in this batch. All fetched."
            fi
            break
        fi

        for id in $customer_ids_batch; do
            total_processed=$((total_processed + 1))
            print_status_stderr "Attempting to delete customer $total_processed: $id"
            if ! stripe customers delete "$id" --api-key "$STRIPE_API_KEY"; then
                print_warning_stderr "Failed to delete customer $id. They might have remaining undeletable resources (e.g., payment methods, final invoices, mandates)."
                failed_deletions=$((failed_deletions + 1))
            fi
            starting_after="$id" # for pagination
        done
        
        has_more=$(echo "$customer_batch_data" | jq -r '.has_more // false')
        if [ "$has_more" != "true" ]; then
            print_status_stderr "No more customers (has_more is false)."
            break
        fi
    done

    print_status_stderr "All found customers ($total_processed) processed for deletion."
    if [ "$failed_deletions" -gt 0 ]; then
        print_warning_stderr "$failed_deletions customer(s) could not be deleted due to dependencies."
    fi
}


# --- Main Execution ---
main() {
    check_dependencies # This will exit if checks fail or pause for 5s

    print_header_stderr "STARTING STRIPE SANDBOX AGGRESSIVE CLEANUP SEQUENCE"
    print_warning_stderr "NO INTERACTIVE CONFIRMATION IS REQUIRED FOR THIS SCRIPT VERSION."

    # Order of operations is important
    delete_all_subscriptions       # Cancel/delete subscriptions first
    delete_all_promotion_codes   # Deactivate promotions (cannot be deleted via CLI)
    delete_all_coupons             # Delete coupons
    delete_all_prices              # Deactivate then attempt to delete prices
    delete_all_products            # Deactivate then attempt to delete products
    delete_all_tax_rates           # Deactivate tax rates (cannot be deleted if used)
    delete_all_webhook_endpoints   # Delete webhooks
    delete_all_customers           # Delete customers last (will attempt pagination)

    print_header_stderr "STRIPE SANDBOX AGGRESSIVE CLEANUP COMPLETE"
    print_status_stderr "Review any warnings above for items that could not be fully deleted due to Stripe API limitations or dependencies."
    print_warning_stderr "Some resources like payment methods or past invoices may persist on customers that could not be deleted."
    print_warning_stderr "You may need to manually clean up further in the Stripe Dashboard if necessary."
}

# Ensure all output from main (especially from stripe CLI calls not explicitly redirected)
# goes to where it's expected. Since we use print_..._stderr for script's own messages,
# stripe CLI output will go to stdout by default if not captured.
# For this script, it's fine for CLI output to go to stdout/stderr as user is watching.
main "$@"