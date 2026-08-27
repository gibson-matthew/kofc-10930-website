from app.services.base_crud_service import BaseCRUDService
from app.models.recognition import Recognition


class RecognitionService(BaseCRUDService):
    def __init__(self):
        super().__init__(Recognition)
