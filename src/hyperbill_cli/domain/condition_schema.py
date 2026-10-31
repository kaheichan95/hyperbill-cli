"""Targeting fields an agent may reference in a bidding condition.

Mirrors ``hyperbill-web/src/lib/conditions/field-types.ts`` and
``hyperbill-web/src/types/context.ts``.
"""

from __future__ import annotations

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
GENDERS = ["male", "female"]
ANIMALS = ["cat", "dog", "bird"]
ATTRIBUTES = [
    "arched eyebrows", "bags under eyes", "bald", "bangs", "big lips", "big nose", "black hair",
    "blond hair", "brown hair", "bushy eyebrows", "chubby", "double chin", "eyeglasses", "goatee",
    "gray hair", "heavy makeup", "high cheekbones", "mouth slightly open", "mustache", "narrow eyes",
    "no beard", "oval face", "pale skin", "pointy nose", "receding hairline", "rosy cheeks",
    "sideburns", "smiling", "straight hair", "wavy hair", "wearing earrings", "wearing hat",
    "wearing lipstick", "wearing necklace", "wearing necktie",
]
OBJECTS = [
    "hat", "cap", "helmet", "hood", "glasses", "sunglasses", "scarf", "jacket", "coat", "vest",
    "shirt", "sweater", "hoodie", "tank top", "pants", "jeans", "shorts", "skirt", "leggings",
    "yoga pants", "sweatpants", "dress", "suit", "overalls", "uniform", "tie", "belt", "mask",
    "glove", "leather shoe", "boot", "sneaker", "sandal", "heel", "bag", "backpack", "handbag",
    "purse", "tote", "briefcase", "duffel", "suitcase", "luggage", "umbrella", "cane",
    "skateboard", "laptop",
]

ARRAY_OPS = ["array-contains", "array-contains-any", "array-contains-all"]
UNION_OPS = ["==", "!=", "in", "not-in"]
NUMBER_OPS = ["<", "<=", "==", ">", ">=", "!="]
TIME_OPS = ["<", "<=", ">", ">="]

FIELDS: dict[str, dict] = {
    "context.time": {"type": "time", "format": "HH:MM (24h, device-local)", "operators": TIME_OPS},
    "context.weekday": {"type": "union", "values": WEEKDAYS, "operators": UNION_OPS},
    "context.impressions": {"type": "number", "description": "headcount in front of the screen", "operators": NUMBER_OPS},
    "context.persons": {
        "type": "array",
        "element": "person",
        "operators": ["array-contains-any", "array-contains-all"],
        "description": "value must be a nested condition over person.* fields",
    },
    "context.animals": {"type": "array", "element": "animal", "values": ANIMALS, "operators": ARRAY_OPS},
    "person.age": {"type": "number", "operators": NUMBER_OPS},
    "person.gender": {"type": "union", "values": GENDERS, "operators": UNION_OPS},
    "person.attributes": {"type": "array", "element": "attribute", "values": ATTRIBUTES, "operators": ARRAY_OPS},
    "person.objects": {"type": "array", "element": "object", "values": OBJECTS, "operators": ARRAY_OPS},
}

EXAMPLE = {
    "condition": {
        "type": "logical",
        "operator": "and",
        "children": [
            {"type": "condition", "field": "context.time", "operator": ">=", "value": "09:00"},
            {
                "type": "condition",
                "field": "context.persons",
                "operator": "array-contains-any",
                "value": {
                    "type": "logical",
                    "operator": "and",
                    "children": [
                        {"type": "condition", "field": "person.gender", "operator": "==", "value": "female"},
                        {"type": "condition", "field": "person.objects", "operator": "array-contains", "value": "handbag"},
                    ],
                },
            },
        ],
    }
}


def describe() -> dict:
    return {
        "format": "biddingLogic JSON: {\"condition\": <AST>} where AST is a condition or logical node",
        "nodes": {
            "condition": {"type": "condition", "field": "<field path>", "operator": "<operator>", "value": "<scalar | list | nested AST>"},
            "logical": {"type": "logical", "operator": "and | or | not", "children": "[AST, ...] (not takes exactly one)"},
        },
        "fields": FIELDS,
        "example": EXAMPLE,
    }
