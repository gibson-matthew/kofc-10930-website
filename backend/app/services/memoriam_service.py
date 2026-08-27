from app.services.base_crud_service import BaseCRUDService
from app.models.memoriam import Memoriam


class MemoriamService(BaseCRUDService):
    def __init__(self):
        super().__init__(Memoriam)
