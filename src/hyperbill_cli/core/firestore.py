"""Firestore REST client acting as the signed-in user.

Every call carries the user's ID token, so Firestore security rules apply
exactly as they do for the web app's browser SDK.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

import requests

from . import firestore_values as values
from .errors import HyperbillError, invalid_input
from .session import Session

TIMEOUT_SECONDS = 60

_OPERATORS = {
    "==": "EQUAL",
    "!=": "NOT_EQUAL",
    "<": "LESS_THAN",
    "<=": "LESS_THAN_OR_EQUAL",
    ">": "GREATER_THAN",
    ">=": "GREATER_THAN_OR_EQUAL",
    "in": "IN",
    "array-contains": "ARRAY_CONTAINS",
}

Filter = tuple[str, str, Any]


@dataclass
class Doc:
    id: str
    name: str
    data: dict[str, Any]
    raw: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, **self.data}


@dataclass
class Page:
    docs: list[Doc]
    next_page_token: str | None


class FirestoreClient:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.root = f"projects/{session.env.project_id}/databases/(default)/documents"
        self.base = f"https://firestore.googleapis.com/v1/{self.root}"

    def get(self, path: str) -> Doc | None:
        response = self._call("GET", f"{self.base}/{path}", allow_404=True)
        return _to_doc(response) if response else None

    def query(
        self,
        parent: str,
        collection: str,
        filters: list[Filter] | None = None,
        order_by: str | None = None,
        descending: bool = False,
        limit: int | None = None,
        page_token: str | None = None,
    ) -> Page:
        structured: dict[str, Any] = {"from": [{"collectionId": collection}]}
        where = _where(filters or [])
        if where:
            structured["where"] = where

        direction = "DESCENDING" if descending else "ASCENDING"
        if order_by:
            structured["orderBy"] = [
                {"field": {"fieldPath": path}, "direction": direction}
                for path in dict.fromkeys([order_by, "__name__"])
            ]
        if page_token:
            if not order_by:
                raise invalid_input("page tokens require an ordered query")
            structured["startAt"] = {"values": _decode_cursor(page_token), "before": False}
        if limit:
            structured["limit"] = limit

        rows = self._call("POST", f"{self._parent_url(parent)}:runQuery", body={"structuredQuery": structured})
        docs = [_to_doc(row["document"]) for row in rows if "document" in row]

        next_token = None
        if order_by and limit and len(docs) == limit:
            next_token = _encode_cursor(docs[-1], order_by)
        return Page(docs=docs, next_page_token=next_token)

    def query_all(self, parent: str, collection: str, filters: list[Filter] | None = None,
                  order_by: str | None = None, descending: bool = False, page_size: int = 500) -> list[Doc]:
        docs: list[Doc] = []
        token: str | None = None
        while True:
            page = self.query(parent, collection, filters, order_by or "__name__", descending, page_size, token)
            docs.extend(page.docs)
            if not page.next_page_token:
                return docs
            token = page.next_page_token

    def aggregate(self, parent: str, collection: str, aggregations: dict[str, tuple[str, str | None]],
                  filters: list[Filter] | None = None) -> dict[str, float]:
        """``aggregations`` maps alias -> ("sum", field) or ("count", None)."""
        structured: dict[str, Any] = {"from": [{"collectionId": collection}]}
        where = _where(filters or [])
        if where:
            structured["where"] = where

        specs = []
        for alias, (kind, field) in aggregations.items():
            spec: dict[str, Any] = {"alias": alias}
            spec[kind] = {"field": {"fieldPath": field}} if field else {}
            specs.append(spec)

        body = {"structuredAggregationQuery": {"structuredQuery": structured, "aggregations": specs}}
        rows = self._call("POST", f"{self._parent_url(parent)}:runAggregationQuery", body=body)
        fields = rows[0].get("result", {}).get("aggregateFields", {}) if rows else {}
        totals: dict[str, float] = {}
        for alias in aggregations:
            totals[alias] = (values.decode(fields[alias]) if alias in fields else None) or 0
        return totals

    def create(self, collection_path: str, data: dict[str, Any]) -> Doc:
        response = self._call("POST", f"{self.base}/{collection_path}", body={"fields": values.encode_fields(data)})
        return _to_doc(response)

    def delete(self, path: str) -> None:
        self._call("DELETE", f"{self.base}/{path}")

    def _parent_url(self, parent: str) -> str:
        return f"{self.base}/{parent}" if parent else self.base

    def _call(self, method: str, url: str, body: Any = None, allow_404: bool = False) -> Any:
        response = self._send(method, url, body, force_refresh=False)
        if response.status_code == 401:
            response = self._send(method, url, body, force_refresh=True)
        if allow_404 and response.status_code == 404:
            return None
        if not response.ok:
            raise _firestore_error(response)
        return response.json() if response.content else None

    def _send(self, method: str, url: str, body: Any, force_refresh: bool) -> requests.Response:
        headers = {"Authorization": f"Bearer {self.session.id_token(force_refresh=force_refresh)}"}
        try:
            return requests.request(method, url, json=body, headers=headers, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise HyperbillError(f"Could not reach Firestore: {exc}", code="network_error") from exc


def _where(filters: list[Filter]) -> dict[str, Any] | None:
    clauses = []
    for field, op, value in filters:
        if op not in _OPERATORS:
            raise invalid_input(f"Unsupported filter operator {op}")
        clauses.append({"fieldFilter": {"field": {"fieldPath": field}, "op": _OPERATORS[op], "value": values.encode(value)}})
    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"compositeFilter": {"op": "AND", "filters": clauses}}


def _to_doc(raw: dict[str, Any]) -> Doc:
    name = raw["name"]
    fields = raw.get("fields", {})
    return Doc(id=name.rsplit("/", 1)[-1], name=name, data=values.decode_fields(fields), raw=fields)


def _encode_cursor(doc: Doc, order_by: str) -> str:
    cursor: list[dict[str, Any]] = []
    if order_by != "__name__":
        cursor.append(_raw_field(doc.raw, order_by))
    cursor.append({"referenceValue": doc.name})
    return base64.urlsafe_b64encode(json.dumps(cursor).encode()).decode().rstrip("=")


def _decode_cursor(token: str) -> list[dict[str, Any]]:
    try:
        padded = token + "=" * (-len(token) % 4)
        cursor = json.loads(base64.urlsafe_b64decode(padded))
    except ValueError as exc:
        raise invalid_input("Malformed page token") from exc
    if not isinstance(cursor, list):
        raise invalid_input("Malformed page token")
    return cursor


def _raw_field(fields: dict[str, Any], path: str) -> dict[str, Any]:
    current: dict[str, Any] = {"mapValue": {"fields": fields}}
    for segment in path.split("."):
        current = current.get("mapValue", {}).get("fields", {}).get(segment, {"nullValue": None})
    return current


def _firestore_error(response: requests.Response) -> HyperbillError:
    try:
        body = response.json()
        if isinstance(body, list):
            body = body[0]
        error = body.get("error", {})
    except (ValueError, AttributeError, IndexError):
        error = {}
    message = error.get("message", f"HTTP {response.status_code}")
    code = {403: "forbidden", 404: "not_found", 400: "invalid_input"}.get(response.status_code, "firestore_error")
    return HyperbillError(f"Firestore: {message}", code=code, status=response.status_code)
