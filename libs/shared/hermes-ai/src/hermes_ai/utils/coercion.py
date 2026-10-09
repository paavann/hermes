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
