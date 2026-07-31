from app.services.base_crud_service import BaseCRUDService
from app.models.uploads import Upload


class UploadService(BaseCRUDService):
    def __init__(self):
        super().__init__(Upload)
