"""
predefined category-to-color mappings.
these are the 10 core categories with fixed pin colors.
when the AI categorizes an event as one of these, the color is
looked up from this dict. For custom/niche categories, the AI
picks both the name and the color.
"""
PREDEFINED_CATEGORIES: dict[str, dict[str, str]] = {
    "CONFLICT": {
        "display_name": "Conflict & Crisis",
        "color": "#EF4444",
    },
    "DISASTER": {
        "display_name": "Disaster",
        "color": "#DC2626",
    },
    "ECONOMY": {
        "display_name": "Economy & Trade",
        "color": "#22C55E",
    },
    "POLITICS": {
        "display_name": "Politics & Governance",
        "color": "#3B82F6",
    },
    "TECHNOLOGY": {
        "display_name": "Technology",
        "color": "#06B6D4",
    },
    "SCIENCE": {
        "display_name": "Science & Research",
        "color": "#8B5CF6",
    },
    "HEALTH": {
        "display_name": "Health & Medicine",
        "color": "#EC4899",
    },
    "ENVIRONMENT": {
        "display_name": "Environment & Climate",
        "color": "#14B8A6",
    },
    "SPORTS": {
        "display_name": "Sports",
        "color": "#F97316",
    },
    "ENTERTAINMENT": {
        "display_name": "Entertainment & Culture",
        "color": "#EAB308",
    },
}