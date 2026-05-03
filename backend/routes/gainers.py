import io
import csv
from flask import Blueprint, jsonify, request, Response
from services.gainer_service import get_gainers_filtered, get_sectors
from services.heatmap_service import build_heatmap_spec
from services.archetype_service import get_archetype_stats

gainers_bp = Blueprint('gainers', __name__)


@gainers_bp.route('/gainers', methods=['GET'])
def list_gainers():
    gainers = get_gainers_filtered(
        date        = request.args.get('date'),
        min_gap     = request.args.get('min_gap',   type=float),
        max_float_m = request.args.get('max_float', type=float),
        min_rvol    = request.args.get('min_rvol',  type=float),
        sector      = request.args.get('sector'),
    )
    return jsonify(gainers)


@gainers_bp.route('/gainers/heatmap', methods=['GET'])
def heatmap():
    return jsonify(build_heatmap_spec())


@gainers_bp.route('/gainers/export', methods=['GET'])
def export_gainers():
    """CSV export — honours the same filter params as /gainers."""
    gainers = get_gainers_filtered(
        date        = request.args.get('date'),
        min_gap     = request.args.get('min_gap',   type=float),
        max_float_m = request.args.get('max_float', type=float),
        min_rvol    = request.args.get('min_rvol',  type=float),
        sector      = request.args.get('sector'),
    )

    if not gainers:
        return Response('', mimetype='text/csv')

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=gainers[0].keys())
    writer.writeheader()
    writer.writerows(gainers)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=gainers.csv'},
    )


@gainers_bp.route('/gainers/sectors', methods=['GET'])
def sectors():
    return jsonify(get_sectors())


@gainers_bp.route('/archetypes', methods=['GET'])
def archetypes():
    return jsonify(get_archetype_stats())
