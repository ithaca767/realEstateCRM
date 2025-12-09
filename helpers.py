def parse_int_or_none(value):
    """Convert a string to int or return None if empty or invalid."""
    try:
        if value is None or value.strip() == "":
            return None
        return int(value)
    except ValueError:
        return None
