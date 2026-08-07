from app.services.base_crud_service import BaseCRUDService
from app.models.user import User


class UserService(BaseCRUDService):
    def __init__(self):
        super().__init__(User)
