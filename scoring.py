from typing import List, Dict
from datetime import datetime
from models import Product, ProductMetrics, ScoringWeights, ScoringThresholds, ProductScore

class ProductScorer:
    def __init__(self, weights: ScoringWeights, thresholds: ScoringThresholds):
        self.weights = weights
        self.thresholds = thresholds
        
    def calculate_base_score(self, metrics: ProductMetrics) -> float:
        """Расчет базового скора на основе метрик"""
        score = 0.0
        
        # Нормализация метрик
        views_score = min(metrics.views / self.thresholds.min_views, 1.0)
        orders_score = min(metrics.orders / self.thresholds.min_orders, 1.0)
        revenue_score = min(metrics.revenue / self.thresholds.min_revenue, 1.0)
        
        # Расчет конверсий
        view_to_cart = metrics.cart_additions / metrics.views if metrics.views > 0 else 0
        cart_to_order = metrics.orders / metrics.cart_additions if metrics.cart_additions > 0 else 0
        
        # Взвешенная сумма
        score += views_score * self.weights.views_weight
        score += view_to_cart * self.weights.cart_weight
        score += cart_to_order * self.weights.orders_weight
        score += revenue_score * self.weights.revenue_weight
        
        return score
    
    def apply_penalties(self, base_score: float, metrics: ProductMetrics) -> tuple[float, List[str]]:
        """Применение штрафов к базовому скору"""
        penalties = []
        final_score = base_score
        
        # Штраф за подозрительно высокую конверсию
        if metrics.views > 0 and metrics.orders / metrics.views > 0.5:
            final_score *= 0.7
            penalties.append("high_conversion_rate")
            
        # Штраф за отсутствие размеров
        if not metrics.sizes_available:
            final_score *= 0.8
            penalties.append("no_sizes_available")
            
        # Штраф за низкую выручку
        if metrics.revenue < self.thresholds.min_revenue:
            final_score *= 0.9
            penalties.append("low_revenue")
            
        return final_score, penalties
    
    def score_product(self, product: Product) -> ProductScore:
        """Расчет финального скора для товара"""
        base_score = self.calculate_base_score(product.metrics)
        final_score, penalties = self.apply_penalties(base_score, product.metrics)
        
        return ProductScore(
            product_id=product.id,
            base_score=base_score,
            final_score=final_score,
            metrics_used=["views", "cart_additions", "orders", "revenue"],
            penalties=penalties,
            timestamp=datetime.now()
        )
        
    def score_products(self, products: List[Product]) -> List[ProductScore]:
        """Расчет скора для списка товаров"""
        return [self.score_product(product) for product in products] 