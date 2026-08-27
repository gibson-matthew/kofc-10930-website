from app.services.base_crud_service import BaseCRUDService
from app.models.merchant_reports import MerchantReport


class MerchantReportService(BaseCRUDService):
    def __init__(self):
        super().__init__(MerchantReport)
