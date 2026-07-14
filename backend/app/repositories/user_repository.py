from app.repositories.base_repository import BaseRepository

class UserRepository(BaseRepository):
    def __init__(self, supabase_client):
        self.client = supabase_client

    def get_profile(self, user_id: str):
        return {"user_id": user_id, "role": "user"}
