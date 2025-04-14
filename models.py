from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductMetrics(BaseModel):
    views: int
    cart_additions: int
    orders: int
    revenue: float
    net_revenue: float
    old_price: float
    new_price: float
    discount: float
    sizes_available: List[str]
    
class Product(BaseModel):
    id: str
    name: str
    category: str
    metrics: ProductMetrics
    created_at: datetime
    updated_at: datetime
    
class ScoringWeights(BaseModel):
    views_weight: float = 0.2
    cart_weight: float = 0.3
    orders_weight: float = 0.4
    revenue_weight: float = 0.5
    discount_weight: float = 0.1
    
class ScoringThresholds(BaseModel):
    min_views: int = 100
    min_orders: int = 5
    min_revenue: float = 1000.0
    
class ProductScore(BaseModel):
    product_id: str
    base_score: float
    final_score: float
    metrics_used: List[str]
    penalties: List[str]
    timestamp: datetime 