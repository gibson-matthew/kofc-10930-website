from app.services.base_crud_service import BaseCRUDService
from app.models.news import News


class NewsService(BaseCRUDService):
    def __init__(self):
        super().__init__(News)
