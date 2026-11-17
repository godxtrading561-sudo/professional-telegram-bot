from supabase_db import save_bot_state, load_bot_state

test_id = "connection_test"

save_bot_state(test_id, {"status": "connected"})

result = load_bot_state(test_id)

print("SUPABASE TEST RESULT:", result)

if result.get("status") != "connected":
    raise RuntimeError("Supabase test failed")

print("SUPABASE CONNECTION SUCCESSFUL!")
