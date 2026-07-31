from app.services.base_crud_service import BaseCRUDService
from app.models.prayer_requests import PrayerRequest

class PrayerService(BaseCRUDService):
    def __init__(self):
        super().__init__(PrayerRequest)
