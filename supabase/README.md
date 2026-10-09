# Supabase migrations

Apply the SQL migrations in timestamp order for durable Pressure Room stories, magic-link identity, project membership, activity events and Trash. The backend uses Supabase Postgres as the sole durable cloud story store. Legacy nullable schema columns remain for compatibility; they are not part of any active external sync implementation.
