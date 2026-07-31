from app.services.base_crud_service import BaseCRUDService
from app.models.market_items import MarketItem

class MarketService(BaseCRUDService):
    def __init__(self):
        super().__init__(MarketItem)
