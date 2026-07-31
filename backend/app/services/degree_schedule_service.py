from app.services.base_crud_service import BaseCRUDService
from app.models.degree_schedule import DegreeSchedule


class DegreeScheduleService(BaseCRUDService):
    def __init__(self):
        super().__init__(DegreeSchedule)
