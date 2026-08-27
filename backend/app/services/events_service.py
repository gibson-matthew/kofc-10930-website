from app.services.base_crud_service import BaseCRUDService
from app.models.events import Event


class EventService(BaseCRUDService):
    def __init__(self):
        super().__init__(Event)
