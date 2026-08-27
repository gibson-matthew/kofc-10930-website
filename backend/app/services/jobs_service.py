from app.services.base_crud_service import BaseCRUDService
from app.models.jobs import Job


class JobService(BaseCRUDService):
    def __init__(self):
        super().__init__(Job)
