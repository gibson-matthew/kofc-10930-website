from app.services.base_crud_service import BaseCRUDService
from app.models.roles import Role


class RoleService(BaseCRUDService):
    def __init__(self):
        super().__init__(Role)
