import json
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from database import get_connection
from validation.decorators import validate_body, validate_query
from validation.schemas import (
    ObservationCreateBody,
    ObservationUpdateBody,
    ObservationFilterQuery,
)

observations_bp = Blueprint('observations', __name__)


# ---------------------------------------------------------------------------
# List / filter
# ---------------------------------------------------------------------------

@observations_bp.route('/observations', methods=['GET'])
@validate_query(ObservationFilterQuery)
def list_observations(qs: ObservationFilterQuery):
    query  = "SELECT * FROM observations WHERE 1=1"
    params = []

    if qs.ticker:
        query += " AND ticker = %s";    params.append(qs.ticker)
    if qs.sentiment:
        query += " AND sentiment = %s"; params.append(qs.sentiment)
    if qs.tag:
        query += " AND tags ILIKE %s";  params.append(f'%{qs.tag}%')
    if qs.date_from:
        query += " AND date >= %s";     params.append(qs.date_from.isoformat())
    if qs.date_to:
        query += " AND date <= %s";     params.append(qs.date_to.isoformat())

    query += " ORDER BY date DESC, created_at DESC LIMIT %s"
    params.append(qs.limit)

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return jsonify([dict(r) for r in rows])


@observations_bp.route('/observations/<ticker>', methods=['GET'])
def get_observations_for_ticker(ticker):
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM observations WHERE ticker = %s ORDER BY date DESC, created_at DESC",
            (ticker,),
        ).fetchall()
    return jsonify([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

@observations_bp.route('/observations', methods=['POST'])
@validate_body(ObservationCreateBody)
def create_observation(data: ObservationCreateBody):
    tags = json.dumps(data.tags)

    now = datetime.now(timezone.utc).isoformat()
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO observations
               (ticker, date, title, body, sentiment, tags, linked_chart_id, created_at, updated_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (data.ticker, data.date.isoformat(), data.title, data.body,
             data.sentiment, tags, data.linked_chart_id, now, now),
        )
        obs_id = cur.fetchone()['id']

    return jsonify({'id': obs_id}), 201


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------

@observations_bp.route('/observations/<int:obs_id>', methods=['PUT'])
@validate_body(ObservationUpdateBody)
def update_observation(data: ObservationUpdateBody, obs_id):
    allowed = {'title', 'body', 'sentiment', 'tags', 'date', 'linked_chart_id'}
    updates = {}

    if data.title is not None:
        updates['title'] = data.title
    if data.body is not None:
        updates['body'] = data.body
    if data.sentiment is not None:
        updates['sentiment'] = data.sentiment
    if data.tags is not None:
        updates['tags'] = json.dumps(data.tags)
    if data.date is not None:
        updates['date'] = data.date.isoformat()
    if data.linked_chart_id is not None:
        updates['linked_chart_id'] = data.linked_chart_id

    updates['updated_at'] = datetime.now(timezone.utc).isoformat()
    set_clause = ', '.join(f'{k} = %s' for k in updates)
    values     = list(updates.values()) + [obs_id]

    with get_connection() as conn:
        row = conn.execute("SELECT id FROM observations WHERE id = %s", (obs_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        conn.execute(f"UPDATE observations SET {set_clause} WHERE id = %s", values)

    return jsonify({'success': True})


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

@observations_bp.route('/observations/<int:obs_id>', methods=['DELETE'])
def delete_observation(obs_id):
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM observations WHERE id = %s", (obs_id,)).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404
        conn.execute("DELETE FROM observations WHERE id = %s", (obs_id,))
    return jsonify({'success': True})
