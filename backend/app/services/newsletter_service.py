from app.services.base_crud_service import BaseCRUDService
from app.models.newsletters import Newsletter

class NewsletterService(BaseCRUDService):
    def __init__(self):
        super().__init__(Newsletter)
