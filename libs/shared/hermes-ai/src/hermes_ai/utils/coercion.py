def coerce_to_str(v: object) -> str:
    match v:
        case None:
            return ""
        case str():
            return v.strip()
        case bool():
            return ""
        case dict():
            for key in ("en", "text", "summary", "headline"):
                val = v.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
            for val in v.values():
                if isinstance(val, str) and val.strip():
                    return val.strip()
            return ""
        case list() | tuple():
            parts = [part for item in v if (part := coerce_to_str(item))]
            return " ".join(parts)
        case _:
            return str(v).strip()


def normalize_enum_token(value: object) -> object:
    if isinstance(value, str):
        return value.strip().upper().replace("-", "_").replace(" ", "_")
    return value


def coerce_country_code(value: object) -> str | None:
    if value is None:
        return None
    cleaned = coerce_to_str(value).upper()
    return cleaned if len(cleaned) == 2 and cleaned.isalpha() else None
