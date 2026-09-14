import os

# Tests explicitly opt into the single-user server database.
os.environ['PRESSURE_ROOM_ALLOW_LOCAL_API'] = 'true'
