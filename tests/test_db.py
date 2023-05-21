# importing everything from our db file
from src.cloud_backend_cache.db import *

# a simple test on the get_database() function to check if the testing works
def test_get_database():
    assert db == get_database()