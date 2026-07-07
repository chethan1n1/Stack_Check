from backend.app.config.settings import settings

def normalize_module_name(name: str) -> str:
    if not name:
        return ""
    # Convert to lowercase
    normalized = str(name).lower().strip()
    # Remove spaces, underscores, hyphens
    for char in [" ", "_", "-"]:
        normalized = normalized.replace(char, "")
    return normalized

