from app.services.base_crud_service import BaseCRUDService
from app.models.user_roles import UserRole


class UserRoleService(BaseCRUDService):
    def __init__(self):
        super().__init__(UserRole)
