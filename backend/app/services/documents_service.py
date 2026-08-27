from app.services.base_crud_service import BaseCRUDService
from app.models.documents import Document


class DocumentService(BaseCRUDService):
    def __init__(self):
        super().__init__(Document)
