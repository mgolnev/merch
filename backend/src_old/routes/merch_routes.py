from flask import Blueprint
from controllers.merchandise_controller import (
    get_all_merchandise,
    get_merchandise,
    create_merchandise,
    update_merchandise,
    delete_merchandise
)

merch_bp = Blueprint('merchandise', __name__)

@merch_bp.route('/merchandise', methods=['GET'])
def get_all():
    return get_all_merchandise()

@merch_bp.route('/merchandise/<int:id>', methods=['GET'])
def get_one(id):
    return get_merchandise(id)

@merch_bp.route('/merchandise', methods=['POST'])
def create():
    return create_merchandise()

@merch_bp.route('/merchandise/<int:id>', methods=['PUT'])
def update(id):
    return update_merchandise(id)

@merch_bp.route('/merchandise/<int:id>', methods=['DELETE'])
def delete(id):
    return delete_merchandise(id) 