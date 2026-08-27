from app.services.base_crud_service import BaseCRUDService
from app.models.programs import Program


class ProgramService(BaseCRUDService):
    def __init__(self):
        super().__init__(Program)
