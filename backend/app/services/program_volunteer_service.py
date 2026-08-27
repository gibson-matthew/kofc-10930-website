from app.services.base_crud_service import BaseCRUDService
from app.models.program_volunteers import ProgramVolunteer


class ProgramVolunteerService(BaseCRUDService):
    def __init__(self):
        super().__init__(ProgramVolunteer)
