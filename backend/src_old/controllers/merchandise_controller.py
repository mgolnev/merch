from flask import jsonify, request
from models.merchandise import Merchandise
from database import db

def get_all_merchandise():
    merchandise = Merchandise.query.all()
    return jsonify([item.to_dict() for item in merchandise])

def get_merchandise(id):
    item = Merchandise.query.get_or_404(id)
    return jsonify(item.to_dict())

def create_merchandise():
    data = request.get_json()
    
    if not all(k in data for k in ('name', 'price')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    item = Merchandise(
        name=data['name'],
        description=data.get('description', ''),
        price=data['price'],
        quantity=data.get('quantity', 0)
    )
    
    db.session.add(item)
    db.session.commit()
    
    return jsonify(item.to_dict()), 201

def update_merchandise(id):
    item = Merchandise.query.get_or_404(id)
    data = request.get_json()
    
    if 'name' in data:
        item.name = data['name']
    if 'description' in data:
        item.description = data['description']
    if 'price' in data:
        item.price = data['price']
    if 'quantity' in data:
        item.quantity = data['quantity']
    
    db.session.commit()
    return jsonify(item.to_dict())

def delete_merchandise(id):
    item = Merchandise.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    return '', 204 