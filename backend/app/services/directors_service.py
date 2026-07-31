from app.services.base_crud_service import BaseCRUDService
from app.models.directors import Director

class DirectorsService(BaseCRUDService):
    def __init__(self):
        super().__init__(Director)
