import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv() 


def get_client(url: str, key: str) -> Client:
    supabase: Client = create_client(url, key)
    return supabase

if __name__ == '__main__':
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")