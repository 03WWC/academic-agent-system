def format_timestamp(timestamp):
    from datetime import datetime
    return datetime.utcfromtimestamp(timestamp).isoformat()
