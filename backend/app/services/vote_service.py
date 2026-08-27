from app.services.base_crud_service import BaseCRUDService
from app.models.votes import Vote


class VoteService(BaseCRUDService):
    def __init__(self):
        super().__init__(Vote)
