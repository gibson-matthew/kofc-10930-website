from app.services.base_crud_service import BaseCRUDService
from app.models.vote_options import VoteOption


class VoteOptionService(BaseCRUDService):
    def __init__(self):
        super().__init__(VoteOption)
