import re
from typing import List, Tuple, Dict
from urllib.parse import quote

def extract_placeholders(path: str) -> List[str]:
    """
    Extracts all placeholders enclosed in curly braces from a path.
    Example: /users/{user_id}?active={is_active} -> ['user_id', 'is_active']
    """
    return re.findall(r"\{([a-zA-Z0-9_]+)\}", path)

def resolve_placeholders(path: str, values: Dict[str, str]) -> str:
    """
    Replaces placeholders in the path with provided values.
    Values are URL-encoded. None values are skipped.
    """
    resolved_path = path
    for key, value in values.items():
        if value is None:
            continue
        placeholder = f"{{{key}}}"
        if placeholder in resolved_path:
            resolved_path = resolved_path.replace(placeholder, quote(str(value), safe="/!"))
    return resolved_path

def validate_path(path: str) -> Tuple[bool, str]:
    """
    Validates the path for malformed placeholders.
    """
    # Check for unclosed braces
    if path.count('{') != path.count('}'):
        return False, "Malformed placeholders: mismatched curly braces."

    # Check for duplicate placeholders
    placeholders = extract_placeholders(path)
    if len(placeholders) != len(set(placeholders)):
        return False, "Duplicate placeholders detected."

    return True, "Valid"
