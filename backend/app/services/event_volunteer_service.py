from app.services.base_crud_service import BaseCRUDService
from app.models.event_volunteers import EventVolunteer


class EventVolunteerService(BaseCRUDService):
    def __init__(self):
        super().__init__(EventVolunteer)
