from app.services.base_crud_service import BaseCRUDService
from app.models.committees import Committee


class CommitteeService(BaseCRUDService):
    def __init__(self):
        super().__init__(Committee)
