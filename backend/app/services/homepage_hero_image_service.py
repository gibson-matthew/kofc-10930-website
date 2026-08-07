from app.services.base_crud_service import BaseCRUDService
from app.models.homepage_hero_images import HomepageHeroImage


class HomepageHeroImageService(BaseCRUDService):
    def __init__(self):
        super().__init__(HomepageHeroImage)
