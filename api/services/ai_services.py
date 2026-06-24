import json
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from pydantic import BaseModel, Field

from accounts.models import Role, Tenant, User
from storefront.models import Category, Inventory, Sale


class AIServiceError(Exception):
    """Base exception for AI service failures that can be shown to API users."""


class AIConfigurationError(AIServiceError):
    pass


class QueryCompilationError(AIServiceError):
    pass


class InventoryItem(BaseModel):
    item_name: str
    category: str
    quantity: int
    confidence_score: float


class DjangoQueryPayload(BaseModel):
    explanation: str = Field(
        description="Plain language explanation of what will be fetched."
    )
    target_model: str = Field(
        description="One of: Tenant, Role, User, Category, Inventory, or Sale."
    )
    tenant_filter: bool = Field(
        default=True,
        description="Always true. The API layer enforces tenant isolation.",
    )
    where_conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Flat Django filter kwargs, for example {'product_name__icontains': 'rice'}.",
    )
    select_related: Optional[List[str]] = Field(default_factory=list)
    prefetch_related: Optional[List[str]] = Field(default_factory=list)
    limit: int = Field(default=50, ge=1, le=200)


MODEL_REGISTRY: Dict[str, Type[models.Model]] = {
    "Tenant": Tenant,
    "Role": Role,
    "User": User,
    "Category": Category,
    "Inventory": Inventory,
    "Sale": Sale,
}

ALLOWED_LOOKUPS = {
    "exact",
    "iexact",
    "contains",
    "icontains",
    "gt",
    "gte",
    "lt",
    "lte",
    "in",
    "isnull",
    "date",
    "year",
    "month",
    "day",
}

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = getattr(settings, "GROQ_API_KEY", None)
        if not api_key:
            raise AIConfigurationError("GROQ_API_KEY is not configured.")
        from groq import Groq

        _client = Groq(api_key=api_key)
    return _client


def convert_text_to_structured_data(user_raw_text: str) -> str:
    chat_completion = _get_client().chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "Convert the user's inventory text into JSON only. "
                    f"The JSON must match this schema: {InventoryItem.model_json_schema()}"
                ),
            },
            {
                "role": "user",
                "content": f"Convert this text into structured data: {user_raw_text}",
            },
        ],
        model="llama-3.1-8b-instant",
        temperature=0,
        response_format={"type": "json_object"},
    )
    return chat_completion.choices[0].message.content


def compile_natural_language_query(user_prompt: str) -> DjangoQueryPayload:
    try:
        payload = _compile_with_groq(user_prompt)
    except AIConfigurationError:
        payload = _compile_with_local_fallback(user_prompt)
    except Exception as exc:
        fallback = _compile_with_local_fallback(user_prompt)
        if fallback:
            payload = fallback
        else:
            raise QueryCompilationError(f"Could not understand the prompt: {exc}") from exc

    if not payload:
        raise QueryCompilationError("Could not understand the prompt.")

    return payload


def generate_answer_from_results(
    user_prompt: str,
    payload: DjangoQueryPayload,
    rows: List[Dict[str, Any]],
) -> str:
    if not rows:
        return (
            f"I could not find any {payload.target_model.lower()} records that match "
            "your question."
        )

    try:
        return _generate_answer_with_groq(user_prompt, payload, rows)
    except Exception:
        return _generate_local_answer(payload, rows)


def validate_query_payload(payload: DjangoQueryPayload) -> DjangoQueryPayload:
    model = MODEL_REGISTRY.get(payload.target_model)
    if not model:
        raise QueryCompilationError(f"Unsupported model '{payload.target_model}'.")

    _validate_filter_conditions(model, payload.where_conditions)
    payload.select_related = _valid_relations(model, payload.select_related or [], many=False)
    payload.prefetch_related = _valid_relations(model, payload.prefetch_related or [], many=True)
    return payload


def _generate_answer_with_groq(
    user_prompt: str,
    payload: DjangoQueryPayload,
    rows: List[Dict[str, Any]],
) -> str:
    sample_rows = rows[:25]
    chat_completion = _get_client().chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a business data assistant. Answer the user's question in "
                    "plain English using only the supplied database rows. Be concise. "
                    "Mention useful totals, counts, or highlights when obvious. Do not "
                    "invent data that is not present."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": user_prompt,
                        "target_model": payload.target_model,
                        "query_explanation": payload.explanation,
                        "total_rows_returned": len(rows),
                        "rows": sample_rows,
                    },
                    default=str,
                ),
            },
        ],
        model="llama-3.1-8b-instant",
        temperature=0.2,
    )
    return chat_completion.choices[0].message.content.strip()


def _generate_local_answer(payload: DjangoQueryPayload, rows: List[Dict[str, Any]]) -> str:
    model_name = payload.target_model.lower()
    count = len(rows)

    if payload.target_model == "Inventory":
        names = _join_preview(row.get("product_name") for row in rows)
        total_stock = sum(_safe_number(row.get("stock_quantity")) for row in rows)
        return (
            f"I found {count} inventory item{'s' if count != 1 else ''}. "
            f"The matching products include {names}. "
            f"Their combined stock quantity is {total_stock:g}."
        )

    if payload.target_model == "Sale":
        total_revenue = sum(_safe_number(row.get("total_price")) for row in rows)
        total_quantity = sum(_safe_number(row.get("quantity")) for row in rows)
        return (
            f"I found {count} sale record{'s' if count != 1 else ''}. "
            f"Together they sold {total_quantity:g} item{'s' if total_quantity != 1 else ''} "
            f"for a total of {total_revenue:g}."
        )

    if payload.target_model == "Category":
        names = _join_preview(row.get("name") for row in rows)
        return f"I found {count} categor{'ies' if count != 1 else 'y'}: {names}."

    if payload.target_model == "User":
        names = _join_preview(row.get("name") or row.get("email") for row in rows)
        return f"I found {count} user{'s' if count != 1 else ''}: {names}."

    if payload.target_model == "Role":
        names = _join_preview(row.get("name") for row in rows)
        return f"I found {count} role{'s' if count != 1 else ''}: {names}."

    return f"I found {count} {model_name} record{'s' if count != 1 else ''}."


def _compile_with_groq(user_prompt: str) -> DjangoQueryPayload:
    system_instruction = f"""
You translate user questions into safe Django QuerySet parameters for a multi-tenant backend.
Return JSON only. Do not return SQL.

Rules:
- target_model must be one of: {", ".join(MODEL_REGISTRY)}.
- tenant_filter must always be true.
- where_conditions must be a flat object of Django filter kwargs.
- Use __icontains for name/text searches.
- Use sold_at for Sale dates, not created_at.
- Use product_name, stock_quantity, max_quantity, reorder_threshold, unit_price for Inventory.
- Use select_related only for single-object relations and prefetch_related only for list relations.
- Keep limit between 1 and 200.

Database schema:
{json.dumps(_database_schema())}

Required output schema:
{json.dumps(DjangoQueryPayload.model_json_schema())}
"""
    chat_completion = _get_client().chat.completions.create(
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt},
        ],
        model="llama-3.3-70b-versatile",
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw_json = chat_completion.choices[0].message.content
    payload_dict = _normalize_payload_dict(json.loads(raw_json))
    return validate_query_payload(DjangoQueryPayload.model_validate(payload_dict))


def _compile_with_local_fallback(user_prompt: str) -> Optional[DjangoQueryPayload]:
    prompt = user_prompt.lower().strip()
    if not prompt:
        return None

    limit = _extract_limit(prompt)

    if any(word in prompt for word in ["sale", "transaction", "revenue", "sold"]):
        conditions: Dict[str, Any] = {}
        if "today" in prompt:
            conditions["sold_at__date"] = "__today__"
        if "cancel" in prompt:
            conditions["is_cancelled"] = True
        return DjangoQueryPayload(
            explanation="Showing sales records that match the prompt.",
            target_model="Sale",
            where_conditions=conditions,
            select_related=["inventory", "created_by"],
            limit=limit,
        )

    if any(word in prompt for word in ["category", "categories"]):
        return DjangoQueryPayload(
            explanation="Showing product categories.",
            target_model="Category",
            where_conditions={},
            limit=limit,
        )

    if any(word in prompt for word in ["user", "users", "staff", "employee", "employees"]):
        return DjangoQueryPayload(
            explanation="Showing users that belong to the current tenant.",
            target_model="User",
            where_conditions={},
            select_related=["role"],
            limit=limit,
        )

    if any(word in prompt for word in ["role", "roles", "permission group"]):
        return DjangoQueryPayload(
            explanation="Showing roles that belong to the current tenant.",
            target_model="Role",
            where_conditions={},
            limit=limit,
        )

    if any(word in prompt for word in ["tenant", "company", "business"]):
        return DjangoQueryPayload(
            explanation="Showing the current tenant record.",
            target_model="Tenant",
            where_conditions={},
            limit=1,
        )

    conditions = {}
    if any(phrase in prompt for phrase in ["low stock", "reorder", "running low"]):
        conditions["stock_quantity__lte"] = "__reorder_threshold__"
    elif match := re.search(r"(?:stock|quantity)\s*(?:under|below|less than|<)\s*(\d+)", prompt):
        conditions["stock_quantity__lt"] = int(match.group(1))
    elif match := re.search(r"(?:stock|quantity)\s*(?:over|above|greater than|>)\s*(\d+)", prompt):
        conditions["stock_quantity__gt"] = int(match.group(1))

    quoted = re.search(r"['\"]([^'\"]+)['\"]", user_prompt)
    if quoted:
        conditions["product_name__icontains"] = quoted.group(1)

    return DjangoQueryPayload(
        explanation="Showing inventory records that match the prompt.",
        target_model="Inventory",
        where_conditions=conditions,
        select_related=["category"],
        limit=limit,
    )


def _normalize_payload_dict(payload: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("query", "DjangoQueryPayload", "properties", "data"):
        if len(payload) == 1 and key in payload and isinstance(payload[key], dict):
            payload = payload[key]
            break

    conditions = payload.get("where_conditions", {})
    if isinstance(conditions, list):
        flat_conditions = {}
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            field_name = condition.get("field") or condition.get("key")
            lookup = condition.get("lookup") or condition.get("operator")
            if field_name and lookup and lookup != "exact":
                field_name = f"{field_name}__{lookup}"
            if field_name:
                flat_conditions[field_name] = condition.get("value")
            else:
                flat_conditions.update(condition)
        payload["where_conditions"] = flat_conditions
    elif conditions is None:
        payload["where_conditions"] = {}

    return payload


def _validate_filter_conditions(model: Type[models.Model], conditions: Dict[str, Any]) -> None:
    for condition in conditions:
        if condition in {"tenant", "tenant_id"}:
            raise QueryCompilationError("Tenant filters are controlled by the API layer.")

        parts = condition.split("__")
        if parts[-1] in ALLOWED_LOOKUPS:
            parts = parts[:-1]

        if not parts:
            raise QueryCompilationError(f"Invalid filter '{condition}'.")

        _resolve_field_path(model, parts)


def _resolve_field_path(model: Type[models.Model], parts: List[str]) -> None:
    current_model = model
    for index, part in enumerate(parts):
        try:
            field = current_model._meta.get_field(part)
        except FieldDoesNotExist as exc:
            raise QueryCompilationError(
                f"'{part}' is not a valid field on {current_model.__name__}."
            ) from exc

        is_last = index == len(parts) - 1
        if is_last:
            return
        if not field.is_relation or not field.related_model:
            raise QueryCompilationError(f"'{part}' is not a relation on {current_model.__name__}.")
        current_model = field.related_model


def _valid_relations(model: Type[models.Model], relations: List[str], many: bool) -> List[str]:
    valid = []
    for relation in relations:
        try:
            field = model._meta.get_field(relation)
        except FieldDoesNotExist:
            continue
        if not field.is_relation:
            continue
        if many and (field.one_to_many or field.many_to_many):
            valid.append(relation)
        elif not many and (field.many_to_one or field.one_to_one):
            valid.append(relation)
    return valid


def _database_schema() -> Dict[str, Any]:
    schema = {}
    for name, model in MODEL_REGISTRY.items():
        fields = []
        relations = {}
        for field in model._meta.get_fields():
            if field.auto_created and not field.concrete:
                if field.is_relation:
                    relations[field.name] = "hasMany"
                continue
            if field.is_relation:
                relations[field.name] = "belongsTo"
                fields.append(f"{field.name}_id")
            else:
                fields.append(field.name)
        schema[name] = {"fields": fields, "relations": relations}
    return schema


def _extract_limit(prompt: str) -> int:
    match = re.search(r"\b(?:top|first|limit|show)\s+(\d+)\b", prompt)
    if not match:
        return 50
    return max(1, min(200, int(match.group(1))))


def resolve_dynamic_condition_value(key: str, value: Any) -> Any:
    if value == "__today__":
        from django.utils import timezone

        return timezone.localdate()
    return value


def is_dynamic_field_comparison(key: str, value: Any) -> bool:
    return key == "stock_quantity__lte" and value == "__reorder_threshold__"


def coerce_decimal_values(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    for row in rows:
        for key, value in row.items():
            if isinstance(value, Decimal):
                row[key] = str(value)
    return rows


def _safe_number(value: Any) -> float:
    if value is None:
        return 0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0


def _join_preview(values) -> str:
    clean_values = [str(value) for value in values if value not in (None, "")]
    if not clean_values:
        return "no named records"
    preview = clean_values[:5]
    joined = ", ".join(preview)
    if len(clean_values) > len(preview):
        joined += f", and {len(clean_values) - len(preview)} more"
    return joined
