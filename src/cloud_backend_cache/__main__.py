import os
from flask import Flask, request, jsonify, Response
from .db import get_database  # importing the get_database for our cache database
import requests
from datetime import datetime, timedelta
import threading
import time
from flask_cors import CORS
from bson import ObjectId
import json

app = Flask(__name__)
CORS(app)  # need to in order to allow the frontend to access the backend api

cache_collection = (
    get_database()
)  # storing the function to get the cache db in a variable


# backend api url:
backend_api_url = "https://cloud-backend-api.onrender.com"  # more reusable when storing the start of the url for the endpoints for the backend api.


# Function to periodically clean up unused cache entries
def cleanup_cache():
    while True:
# delete cache entries that haven't been accessed for a certain duration, in this its 10 days
        cache_collection.delete_many({"last_accessed": {"$lt": datetime.now() - timedelta(days=10)}})
# sleep for a specific interval (e.g., 24 hours) before running the cleanup operation again
        time.sleep(24 * 60 * 60)

# start a background thread to perform cache cleanup periodically
cleanup_thread = threading.Thread(target=cleanup_cache)
cleanup_thread.start()


def validate_security_key(key):
    expected_key = "assignment2"

    # Compare the provided key with the expected key
    if key == expected_key:
        return True

    return False

#caches the contacts
@app.route("/contacts")
def get_contacts(update_cache=False):
    cache_key = "contacts"
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers

    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        if update_cache:
            # Delete the old collection and create a new one with the updated info
            cache_collection.delete_one({"_id": cache_key})

        cache_entry = cache_collection.find_one({"_id": cache_key})
        if cache_entry:
            data = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")
            if last_accessed is not None:
                # Update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            backend_endpoint = "/contacts"
            response = requests.get(backend_api_url + backend_endpoint)
            data = response.json()

            cache_collection.insert_one(
                {"_id": cache_key, "data": data, "last_accessed": datetime.now()}
            )

        return jsonify(data)
    else:
        return jsonify({"error": "Invalid security key"}), 401


# sjekke om man kan lete i den all contacts cachen etter id???
@app.route("/contacts/<string:id>")  # contacts by id
def get_contactById(id):
    cache_key = f"contacts_{id}"
    cache_entry = cache_collection.find_one({"_id": cache_key})
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers

    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        if cache_entry:
            data = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")
            if last_accessed is not None:
                # Update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            backend_endpoint = f"/contacts/{id}"
            response = requests.get(backend_api_url + backend_endpoint)
            data = response.json()

            cache_collection.insert_one(
                {"_id": cache_key, "data": data, "last_accessed": datetime.now()}
            )

        return jsonify(data)
    else:
        return jsonify({"error": "Invalid security key"}), 401

# checking for spesific contact and returns as vcard
@app.route("/contacts/<string:id>/vcard", methods=["GET"])
def get_by_id_vcard(id):
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers

    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        cache_key = f"vcard_{id}"
        cache_entry = cache_collection.find_one({"_id": cache_key})
        if cache_entry:
            vcard_content = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")
            if last_accessed is not None:
                # Update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            # Fetch the data from the backend database
            backend_endpoint = f"/contacts/{id}/vcard"
            response = requests.get(backend_api_url + backend_endpoint)
            if response.status_code == 404:
                return jsonify({"error": "Not a valid id"}), 404
            elif response.status_code == 401:
                return jsonify({"error": "Unauthorized"}), 401
            vcard_content = response.content

            # Store the fetched data in the cache
            cache_collection.insert_one(
                {
                    "_id": cache_key,
                    "data": vcard_content,
                    "last_accessed": datetime.now(),
                }
            )

        return Response(vcard_content, mimetype="text/vcard")
    else:
        return jsonify({"error": "Invalid security key"}), 401

#Forwards the upload
@app.route("/cache/upload.html", methods=["POST"])
def cache_upload_vcard():
    security_key = request.form.get(
        "securityKey"
    )  # Retrieve the security key from the form data

    if not validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        return jsonify({"error": "Invalid security key"}), 401

    vcard_file = request.files["file"]

    # Forward the POST request to the backend API
    backend_url = backend_api_url + "/upload.html"  # Replace with your backend API URL
    response = requests.post(backend_url, files={"file": vcard_file})

    # Update the cache after successful file upload
    if response.status_code == 200:
        get_contacts(update_cache=True)

    # Return the response from the backend API to the client
    return response.content, response.status_code, response.headers.items()

@app.route("/contacts/vcard", methods=["GET"])
def get_all_contacts_vcard():
    cache_key = "contacts_vcard"
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers

    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        cache_entry = cache_collection.find_one({"_id": cache_key})

        if cache_entry:
            vcards = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")

            if last_accessed is not None:
                # Update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            # Fetch data from the backend
            backend_endpoint = "/contacts/vcard"
            response = requests.get(backend_api_url + backend_endpoint)

            if response.status_code == 200:
                vcards = (
                    response.content
                )  # Assuming the backend response is the vCard content
                cache_collection.insert_one(
                    {"_id": cache_key, "data": vcards, "last_accessed": datetime.now()}
                )
            else:
                return jsonify({"error": "Failed to fetch data from the backend"}), 500

        return Response(vcards, mimetype="text/vcard")
    else:
        return jsonify({"error": "Invalid security key"}), 401

#forwards the download
@app.route("/contacts/vcard/download", methods=["GET"])
def forward_get_all_vcards():
    cache_key = "contacts_vcard_download"
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers

    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        cache_entry = cache_collection.find_one({"_id": cache_key})

        if cache_entry:
            vcard_content = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")

            if last_accessed is not None:
                # Update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            # Fetch data from the backend
            backend_endpoint = "/contacts/vcard/download"
            response = requests.get(backend_api_url + backend_endpoint)
            vcard_content = response.content
            cache_collection.insert_one(
                {
                    "_id": cache_key,
                    "data": vcard_content,
                    "last_accessed": datetime.now(),
                }
            )

        # Create the response with the vCard content
        response = Response(vcard_content, mimetype="text/x-vcard")
        response.headers.set(
            "Content-Disposition", "attachment", filename="all_contacts.vcf"
        )
        return response
    else:
        return Response(status=401)

#Cache for the vcard inside json structure
@app.route("/contacts/vcard/json", methods=["GET"])
def get_all_contacts_vcard_json(update_cache=False):
    cache_key = "contacts_vcard_json"
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers
    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        if update_cache:
            cache_collection.delete_one({"_id": cache_key})
        cache_entry = cache_collection.find_one({"_id": cache_key})

        if cache_entry:
            data = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")

            if last_accessed is not None:
                # update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            # Fetch data from the backend
            backend_endpoint = "/contacts/vcard/json"
            response = requests.get(backend_api_url + backend_endpoint)
            data = response.json()
            cache_collection.insert_one(
                {"_id": cache_key, "data": data, "last_accessed": datetime.now()}
            )
        return data
    else:
        return jsonify({"error": "Invalid security key"}), 401

#caches the vcard in json structure using id 
@app.route("/contacts/<string:id>/vcard/json", methods=["GET"])
def get_by_id_vcard_json(id):
    cache_key = f"vcard_json{id}"
    cache_entry = cache_collection.find_one({"_id": cache_key})
    security_key = request.headers.get(
        "X-Security-Key"
    )  # Get the security key from the request headers
    if validate_security_key(
        security_key
    ):  # Implement your security key validation logic
        if cache_entry:
            data = cache_entry["data"]
            last_accessed = cache_entry.get("last_accessed")
            if last_accessed is not None:
                # Update last_accessed timestamp to the current time
                cache_collection.update_one(
                    {"_id": cache_key}, {"$set": {"last_accessed": datetime.now()}}
                )
        else:
            # Fetch the data from the backend database
            backend_endpoint = f"/contacts/{id}/vcard/json"
            response = requests.get(backend_api_url + backend_endpoint)
            data = response.json()

            # Store the fetched data in the cache
            cache_collection.insert_one(
                {"_id": cache_key, "data": data, "last_accessed": datetime.now()}
            )
        return data
    else:
        return jsonify({"error": "Invalid security key"}), 401


if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("PORT", default=4500), host="0.0.0.0")
