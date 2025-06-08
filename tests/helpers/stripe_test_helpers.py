import os
import time
import logging
import stripe

logger = logging.getLogger(__name__)

# Ensure we always use the API key from env when helpers are imported
stripe.api_key = os.getenv("STRIPE_API_KEY", "")


def create_test_clock() -> stripe.test_helpers.TestClock:
    """Create a Stripe Test Clock frozen at current time.

    Returns:
        stripe.test_helpers.TestClock: The created test clock object.
    """
    now_ts = int(time.time())
    clock = stripe.test_helpers.TestClock.create(frozen_time=now_ts)
    logger.info(f"Created Stripe Test Clock {clock.id} frozen at {now_ts}")
    return clock


def advance_clock(clock_id: str, seconds: int = 120):
    """Advance a Stripe Test Clock by a given number of seconds.

    Args:
        clock_id (str): The ID of the test clock to advance.
        seconds (int, optional): How many seconds to advance. Defaults to 120.
    """
    new_time = int(time.time()) + seconds
    stripe.test_helpers.TestClock.advance(test_clock=clock_id, frozen_time=new_time)
    logger.info(f"Advanced Stripe Test Clock {clock_id} to {new_time}")


def delete_test_clock(clock_id: str):
    """Delete a Stripe Test Clock.

    Args:
        clock_id (str): The ID of the test clock to delete.
    """
    try:
        stripe.test_helpers.TestClock.delete(clock_id)
        logger.info(f"Deleted Stripe Test Clock {clock_id}")
    except stripe.error.InvalidRequestError:
        # Clock already deleted or not found – safe to ignore
        logger.warning(f"Stripe Test Clock {clock_id} already deleted or not found.") 