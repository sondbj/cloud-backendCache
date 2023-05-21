from pymongo import MongoClient  # import our MongoDB client


def get_database():  # function to get the database
    CONNECTION_STRING = "mongodb+srv://mathiakk:123@cluster0.qalzrkm.mongodb.net/test"  # we connect to our DB
    client = MongoClient(
        CONNECTION_STRING
    )  # we create a client with our connection string
    db = client[
        "cache_db"
    ]  # we create a database called "Cloud-technologies, if it doesnt already exist"
    return db["cache_collection"]


# here we try to access our database, and if its a success it prints a msg
try:
    db = get_database()  # we try to get the database
    print("Database connection established")
except:  # if not success print this msg
    print("Database connection failed")
