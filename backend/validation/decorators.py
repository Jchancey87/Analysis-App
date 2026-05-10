"""
validation/decorators.py
------------------------
Thin Flask decorators that validate request data against a Pydantic v2 model
and inject the validated model as the first positional argument to the route.

Usage
-----
    from validation.decorators import validate_body, validate_query
    from validation.schemas import MyBodySchema, MyQuerySchema

    @bp.route('/foo', methods=['POST'])
    @validate_body(MyBodySchema)
    def foo(data: MyBodySchema):
        ...

    @bp.route('/bar', methods=['GET'])
    @validate_query(MyQuerySchema)
    def bar(params: MyQuerySchema):
        ...

On validation failure both decorators return:
    HTTP 422  {"errors": [{"field": "field_name", "msg": "human message"}]}
"""

from __future__ import annotations

import functools
from typing import Type, TypeVar

from flask import jsonify, request
from pydantic import BaseModel, ValidationError

M = TypeVar("M", bound=BaseModel)


def _format_errors(exc: ValidationError) -> list[dict]:
    """Convert a Pydantic ValidationError into a flat list of {field, msg} dicts."""
    errors = []
    for err in exc.errors(include_url=False):
        field = ".".join(str(loc) for loc in err["loc"]) if err["loc"] else "__root__"
        errors.append({"field": field, "msg": err["msg"]})
    return errors


def validate_body(schema: Type[M]):
    """
    Decorator for POST/PUT routes that expect a JSON body.
    Parses request.get_json() and validates it against `schema`.
    Injects the validated model as the first argument to the wrapped function.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw = request.get_json(silent=True) or {}
            try:
                data = schema.model_validate(raw)
            except ValidationError as exc:
                return jsonify({"errors": _format_errors(exc)}), 422
            return fn(data, *args, **kwargs)
        return wrapper
    return decorator


def validate_query(schema: Type[M]):
    """
    Decorator for GET routes that read from request.args (query string).
    All query-string values arrive as strings; schemas should use field
    validators or Pydantic's coercion to convert to the correct type.
    Injects the validated model as the first argument to the wrapped function.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            raw = dict(request.args)
            # Flatten single-item lists that ImmutableMultiDict produces
            raw = {k: (v[0] if isinstance(v, list) and len(v) == 1 else v)
                   for k, v in raw.items()}
            try:
                params = schema.model_validate(raw)
            except ValidationError as exc:
                return jsonify({"errors": _format_errors(exc)}), 422
            return fn(params, *args, **kwargs)
        return wrapper
    return decorator
