from models import ScoringWeights, ScoringThresholds

# Веса для различных метрик
DEFAULT_WEIGHTS = ScoringWeights(
    views_weight=0.2,
    cart_weight=0.3,
    orders_weight=0.4,
    revenue_weight=0.5,
    discount_weight=0.1
)

# Пороговые значения для метрик
DEFAULT_THRESHOLDS = ScoringThresholds(
    min_views=100,
    min_orders=5,
    min_revenue=1000.0
)

# Настройки для различных категорий товаров
CATEGORY_WEIGHTS = {
    "clothing": ScoringWeights(
        views_weight=0.25,
        cart_weight=0.35,
        orders_weight=0.45,
        revenue_weight=0.55,
        discount_weight=0.15
    ),
    "shoes": ScoringWeights(
        views_weight=0.3,
        cart_weight=0.4,
        orders_weight=0.5,
        revenue_weight=0.6,
        discount_weight=0.2
    ),
    "accessories": ScoringWeights(
        views_weight=0.2,
        cart_weight=0.3,
        orders_weight=0.4,
        revenue_weight=0.5,
        discount_weight=0.1
    )
}

# Настройки для различных сезонов
SEASONAL_MULTIPLIERS = {
    "summer": {
        "clothing": 1.2,
        "shoes": 1.3,
        "accessories": 1.1
    },
    "winter": {
        "clothing": 1.3,
        "shoes": 1.4,
        "accessories": 1.2
    },
    "spring": {
        "clothing": 1.1,
        "shoes": 1.2,
        "accessories": 1.0
    },
    "autumn": {
        "clothing": 1.2,
        "shoes": 1.3,
        "accessories": 1.1
    }
}

# Настройки для различных типов скидок
DISCOUNT_MULTIPLIERS = {
    "regular": 1.0,
    "promo": 1.2,
    "clearance": 1.5
} 