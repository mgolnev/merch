from fastapi import FastAPI, HTTPException
from typing import List
from datetime import datetime
import pandas as pd
from models import Product, ProductMetrics, ProductScore
from scoring import ProductScorer
from config import DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS, CATEGORY_WEIGHTS, SEASONAL_MULTIPLIERS

app = FastAPI(title="Gloria Jeans AutoMerch System")

# Инициализация скорера
scorer = ProductScorer(DEFAULT_WEIGHTS, DEFAULT_THRESHOLDS)

@app.post("/score-products")
async def score_products(products: List[Product]) -> List[ProductScore]:
    """
    Расчет скора для списка товаров
    """
    try:
        return scorer.score_products(products)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/product/{product_id}")
async def get_product_score(product_id: str) -> ProductScore:
    """
    Получение скора для конкретного товара
    """
    # Здесь должна быть логика получения товара из базы данных
    # Пока что возвращаем заглушку
    raise HTTPException(status_code=501, detail="Not implemented yet")

@app.post("/update-weights")
async def update_weights(category: str, weights: dict):
    """
    Обновление весов для категории товаров
    """
    if category not in CATEGORY_WEIGHTS:
        raise HTTPException(status_code=400, detail="Invalid category")
    
    # Обновление весов
    CATEGORY_WEIGHTS[category] = ScoringWeights(**weights)
    return {"status": "success", "message": f"Weights updated for {category}"}

@app.get("/seasonal-multipliers")
async def get_seasonal_multipliers(season: str):
    """
    Получение сезонных множителей
    """
    if season not in SEASONAL_MULTIPLIERS:
        raise HTTPException(status_code=400, detail="Invalid season")
    
    return SEASONAL_MULTIPLIERS[season]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 