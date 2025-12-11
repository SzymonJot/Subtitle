import os

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()


def get_client() -> Client:
    supabase: Client = create_client(
        os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
    )
    return supabase


if __name__ == "__main__":
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
