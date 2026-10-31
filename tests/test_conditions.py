import json

import pytest

from hyperbill_cli.core.errors import HyperbillError
from hyperbill_cli.domain.condition_schema import EXAMPLE
from hyperbill_cli.domain.conditions import load_bidding_logic


def test_example_is_valid():
    assert load_bidding_logic(json.dumps(EXAMPLE)) == EXAMPLE


def test_bare_ast_is_wrapped():
    ast = {"type": "condition", "field": "context.weekday", "operator": "in", "value": ["monday", "friday"]}
    assert load_bidding_logic(json.dumps(ast)) == {"condition": ast}


def test_none_clears_condition():
    assert load_bidding_logic("none") == {"condition": None}


@pytest.mark.parametrize("ast", [
    {"type": "condition", "field": "context.time", "operator": "==", "value": "09:00"},
    {"type": "condition", "field": "context.time", "operator": ">=", "value": "25:00"},
    {"type": "condition", "field": "context.weekday", "operator": "==", "value": "funday"},
    {"type": "condition", "field": "person.age", "operator": ">", "value": 30},
    {"type": "condition", "field": "context.persons", "operator": "array-contains-any",
     "value": {"type": "condition", "field": "context.time", "operator": ">", "value": "09:00"}},
    {"type": "logical", "operator": "not", "children": []},
    {"type": "condition", "field": "context.animals", "operator": "array-contains-any", "value": "dog"},
])
def test_rejects_invalid(ast):
    with pytest.raises(HyperbillError) as info:
        load_bidding_logic(json.dumps(ast))
    assert info.value.code == "invalid_input"
