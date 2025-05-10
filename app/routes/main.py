from flask import Blueprint, render_template
from app.services.weights_service import get_current_weights

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@main_bp.route('/weights')
def weights_page():
    """Страница настройки весов"""
    weights = get_current_weights()
    return render_template('weights.html', weights=weights) 