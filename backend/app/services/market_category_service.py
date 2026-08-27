from app.services.base_crud_service import BaseCRUDService
from app.models.market_categories import MarketCategory


class MarketCategoryService(BaseCRUDService):
    def __init__(self):
        super().__init__(MarketCategory)
