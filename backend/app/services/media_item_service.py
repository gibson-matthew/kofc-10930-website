from app.services.base_crud_service import BaseCRUDService
from app.models.media_items import MediaItem


class MediaItemService(BaseCRUDService):
    def __init__(self):
        super().__init__(MediaItem)
