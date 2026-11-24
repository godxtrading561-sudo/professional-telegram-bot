from supabase_db import get_client


def main():
    client = get_client()

    if client is None:
        print("Supabase credentials are missing.")
        return

    try:
        result = (
            client.table("bot_state")
            .select("*")
            .limit(1)
            .execute()
        )
        print("Supabase connection successful.")
        print("Returned rows:", len(result.data))
    except Exception as exc:
        print("Supabase connection failed:", exc)


if __name__ == "__main__":
    main()
