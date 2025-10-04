# import os
# from supabase import create_client, Client
# from dotenv import load_dotenv
# load_dotenv() 

# url: str = os.environ.get("SUPABASE_URL")
# key: str = os.environ.get("SUPABASE_KEY")
# supabase: Client = create_client(url, key)


# all_jobs = (
#     supabase.table("jobs")
#     .select("*")
#     .execute()
# )


# response = (
#     supabase.table("jobs")
#     .insert({})
#     .execute()
# )

# def insert_date():
#     try:
#         response = (
#             supabase.table("characters")
#             .insert([
#                 {"id": 1, "name": "Frodo"},
#                 {"id": 2, "name": "Sam"},
#             ])
#             .execute()
#         )
#         return response
#     except Exception as exception:
#         return exception


# response = (
#     supabase.table("instruments")
#     .update({"name": "piano"})
#     .eq("id", 1)
#     .execute()
# )