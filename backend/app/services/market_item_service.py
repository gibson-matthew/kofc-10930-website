from app.services.base_crud_service import BaseCRUDService
from app.models.market_items import MarketItem


class MarketItemService(BaseCRUDService):
    def __init__(self):
        super().__init__(MarketItem)
