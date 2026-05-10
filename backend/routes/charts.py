import json
import os
from flask import Blueprint, jsonify, request, send_from_directory
from database import get_connection
from services.chart_service import validate_tags, save_chart_image, VALID_TAGS
from config import Config
from validation.decorators import validate_body
from validation.schemas import ChartUpdateBody, ChartUploadForm
from pydantic import ValidationError

charts_bp = Blueprint('charts', __name__)


def _sync_chart_tags(conn, chart_id: int, tags: list):
    """Replace all chart_tags rows for chart_id with the new tag list."""
    conn.execute("DELETE FROM chart_tags WHERE chart_id = %s", (chart_id,))
    for tag in tags:
        tag = str(tag).strip()
        if tag:
            conn.execute(
                "INSERT INTO chart_tags (chart_id, tag) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (chart_id, tag),
            )


@charts_bp.route('/charts', methods=['POST'])
def upload_chart():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided (field name: image)'}), 400

    file = request.files['image']

    # Validate multipart form data via Pydantic (inline — no decorator for multipart)
    try:
        form = ChartUploadForm.model_validate(dict(request.form))
    except ValidationError as exc:
        errors = [{"field": ".".join(str(l) for l in e["loc"]), "msg": e["msg"]}
                  for e in exc.errors(include_url=False)]
        return jsonify({"errors": errors}), 422

    tags    = form.tags
    invalid = validate_tags(tags)
    if invalid:
        return jsonify({'error': f'Invalid tags: {invalid}', 'valid_tags': VALID_TAGS}), 422

    try:
        image_path = save_chart_image(file, form.ticker, form.capture_date.isoformat())
    except ValueError as e:
        return jsonify({'error': str(e)}), 415

    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO chart_captures
               (ticker, capture_date, timeframe, image_path, setup_type,
                cleanliness_score, tags, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (form.ticker, form.capture_date.isoformat(), form.timeframe, image_path,
             form.setup_type, form.cleanliness_score, json.dumps(tags), form.notes),
        )
        chart_id = cur.fetchone()['id']
        _sync_chart_tags(conn, chart_id, tags)

    return jsonify({'id': chart_id, 'image_path': image_path}), 201


@charts_bp.route('/charts', methods=['GET'])
def list_charts():
    ticker     = (request.args.get('ticker') or '').upper().strip()
    setup_type = request.args.get('setup_type')
    tag        = request.args.get('tag')
    date_from  = request.args.get('date_from')
    date_to    = request.args.get('date_to')
    min_clean  = request.args.get('min_cleanliness', type=int)

    query  = "SELECT DISTINCT cc.* FROM chart_captures cc"
    params = []

    if tag:
        query += " JOIN chart_tags ct ON ct.chart_id = cc.id AND ct.tag = %s"
        params.append(tag)

    query += " WHERE 1=1"

    if ticker:
        query += " AND cc.ticker = %s";     params.append(ticker)
    if setup_type:
        query += " AND cc.setup_type = %s"; params.append(setup_type)
    if date_from:
        query += " AND cc.capture_date >= %s"; params.append(date_from)
    if date_to:
        query += " AND cc.capture_date <= %s"; params.append(date_to)
    if min_clean is not None:
        query += " AND cc.cleanliness_score >= %s"; params.append(min_clean)

    query += " ORDER BY cc.capture_date DESC, cc.created_at DESC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return jsonify([dict(r) for r in rows])


@charts_bp.route('/charts/<int:chart_id>', methods=['GET'])
def get_chart(chart_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM chart_captures WHERE id = %s", (chart_id,)
        ).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))


@charts_bp.route('/charts/<int:chart_id>', methods=['PUT'])
@validate_body(ChartUpdateBody)
def update_chart(data: ChartUpdateBody, chart_id):
    updates = {}

    if data.notes is not None:
        updates['notes'] = data.notes
    if data.cleanliness_score is not None:
        updates['cleanliness_score'] = data.cleanliness_score
    if data.setup_type is not None:
        updates['setup_type'] = data.setup_type
    if data.timeframe is not None:
        updates['timeframe'] = data.timeframe

    tag_list = None
    if data.tags is not None:
        invalid = validate_tags(data.tags)
        if invalid:
            return jsonify({'error': f'Invalid tags: {invalid}', 'valid_tags': VALID_TAGS}), 422
        updates['tags'] = json.dumps(data.tags)
        tag_list = data.tags

    set_clause = ', '.join(f'{k} = %s' for k in updates)
    values     = list(updates.values()) + [chart_id]

    with get_connection() as conn:
        conn.execute(f"UPDATE chart_captures SET {set_clause} WHERE id = %s", values)
        if tag_list is not None:
            _sync_chart_tags(conn, chart_id, tag_list)

    return jsonify({'success': True})


@charts_bp.route('/charts/<int:chart_id>', methods=['DELETE'])
def delete_chart(chart_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT image_path, gemini_image_path FROM chart_captures WHERE id = %s",
            (chart_id,)
        ).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404

        for path_field in ('image_path', 'gemini_image_path'):
            p = row[path_field]
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass

        # chart_tags rows deleted by CASCADE
        conn.execute("DELETE FROM chart_captures WHERE id = %s", (chart_id,))

    return jsonify({'success': True})


@charts_bp.route('/charts/<int:chart_id>/gemini-import', methods=['POST'])
def gemini_import(chart_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT ticker, capture_date FROM chart_captures WHERE id = %s",
            (chart_id,)
        ).fetchone()
        if not row:
            return jsonify({'error': 'Not found'}), 404

        ticker = row['ticker']
        capture_date = row['capture_date']

    if request.is_json:
        data = request.get_json() or {}
        analysis_text = data.get('analysis_text', '').strip()
        image_file = None
    else:
        analysis_text = request.form.get('analysis_text', '').strip()
        image_file = request.files.get('annotated_image') or request.files.get('image')

    image_path = None
    if image_file:
        try:
            image_path = save_chart_image(
                image_file,
                ticker=ticker,
                capture_date=capture_date,
                subfolder='annotated'
            )
        except ValueError as e:
            return jsonify({'error': str(e)}), 415

    with get_connection() as conn:
        if image_path:
            conn.execute(
                """UPDATE chart_captures
                   SET gemini_annotation = %s,
                       llm_annotation = %s,
                       gemini_image_path = %s,
                       gemini_imported_at = NOW()
                   WHERE id = %s""",
                (analysis_text, analysis_text, image_path, chart_id)
            )
        else:
            conn.execute(
                """UPDATE chart_captures
                   SET gemini_annotation = %s,
                       llm_annotation = %s,
                       gemini_imported_at = NOW()
                   WHERE id = %s""",
                (analysis_text, analysis_text, chart_id)
            )

    return jsonify({
        'success': True,
        'gemini_image_path': image_path,
        'analysis_text': analysis_text
    })
