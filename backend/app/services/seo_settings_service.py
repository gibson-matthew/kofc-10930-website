from app.services.base_crud_service import BaseCRUDService
from app.models.seo_settings import SEOSettings


class SEOSettingsService(BaseCRUDService):
    def __init__(self):
        super().__init__(SEOSettings)
