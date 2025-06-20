from datetime import datetime, timedelta

# Define time threshold in hours
RECENT_THRESHOLD_HOURS = 12

def is_recent(past_time):
    """Return True if past_time is within the last RECENT_THRESHOLD_HOURS"""
    if not past_time:
        return False
    now = datetime.utcnow()
    return (now - past_time) <= timedelta(hours=RECENT_THRESHOLD_HOURS)

def message_contains_reference_words(text):
    reference_words = ["again", "as mentioned", "like before", "same issue", "follow up", "earlier", "previous"]
    lower_text = text.lower()
    return any(phrase in lower_text for phrase in reference_words)
