from app.services.base_crud_service import BaseCRUDService
from app.models.audit_log import AuditLog


class AuditLogService(BaseCRUDService):
    def __init__(self):
        super().__init__(AuditLog)
