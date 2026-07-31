from app.services.base_crud_service import BaseCRUDService
from app.models.links import Link


class LinkService(BaseCRUDService):
    def __init__(self):
        super().__init__(Link)
