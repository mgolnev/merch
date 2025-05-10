from typing import List, Tuple, Any

class QueryBuilder:
    """Класс для построения SQL-запросов"""
    def __init__(self):
        self.conditions = []
        self.params = []
    
    def add_condition(self, condition: str, param: Any = None):
        """Добавление условия в WHERE"""
        self.conditions.append(condition)
        if param is not None:
            self.params.append(param)
    
    def build(self) -> Tuple[str, List[Any]]:
        """Построение финального SQL-запроса"""
        where_clause = " AND ".join(self.conditions) if self.conditions else "1=1"
        return where_clause, self.params 