from app.services.base_crud_service import BaseCRUDService
from app.models.media_albums import MediaAlbum


class MediaAlbumService(BaseCRUDService):
    def __init__(self):
        super().__init__(MediaAlbum)