from app.services.base_crud_service import BaseCRUDService
from app.models.vote_cast import VoteCast


class VoteCastService(BaseCRUDService):
    def __init__(self):
        super().__init__(VoteCast)
