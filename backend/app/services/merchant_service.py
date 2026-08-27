from app.services.base_crud_service import BaseCRUDService
from app.models.merchants import Merchant


class MerchantService(BaseCRUDService):
    def __init__(self):
        super().__init__(Merchant)
