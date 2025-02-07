import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()  # take environment variables from .env.

CONTAINER_NAME = "active-docker-images"
NUMBER_OF_DAYS_TO_CONSIDER = 15
NUMBER_OF_DAYS_TO_CONSIDER_FOR_SANBOX = 2
REGISTRY_BASE_URL = " "
REGISTRY_USER = os.getenv("registry-username")
REGISTRY_PASSWORD = os.getenv("registry-password")
DELETE_DRY_RUN = True

def log_error(message):
    print(f"ERROR: {message}")

# onprem, static images
def static_images():
    return [
        " <enter the file to white list> ", 
    ]


def fetch_active_images_from_blob():
    default_blob_sas_url = ""
    blob_sas_url = os.getenv("blob_sas_url", default_blob_sas_url)
    blob_service_client = BlobServiceClient(blob_sas_url)
    print("Started")

    sandbox_days = NUMBER_OF_DAYS_TO_CONSIDER_FOR_SANBOX
    default_days = NUMBER_OF_DAYS_TO_CONSIDER

    # Get today's date
    now = datetime.now(timezone.utc)

    # Generate allowed dates for sandbox and default
    sandbox_date_range = {(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(sandbox_days)}
    default_date_range = {(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(default_days)}

    print(f"Sandbox Days: {sandbox_date_range}")
    print(f"Default Days: {default_date_range}")

    active_images = set()
    try:
        container_client = blob_service_client.get_container_client(container=CONTAINER_NAME)
        blob_list = container_client.list_blobs()

        for blob in blob_list:
            try:
                splits = blob.name.split("/")
                if len(splits) < 2:
                    continue  # Invalid blob path, skip

                folder_date = splits[0]  # First part is the date
                cluster_folder = splits[1]  # Second part identifies the cluster

                # Check if the blob belongs to sandbox folders
                if "sandbox" in cluster_folder.lower() and folder_date in sandbox_date_range:
                    print(f"Processing sandbox folder blob: {blob.name}")
                elif folder_date in default_date_range and not "sandbox" in cluster_folder.lower():
                    print(f"Processing default folder blob: {blob.name}")
                else:
                    continue  # Skip folders not in the allowed ranges

                # Fetch blob data
                blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob.name)
                blob_data = blob_client.download_blob().readall()
                image_list = blob_data.decode('utf-8').splitlines()
                active_images.update(image_list)

            except Exception as e:
                log_error(f"Failed to process blob {blob.name}: {str(e)}")

        return active_images
    except Exception as e:
        log_error(f"Failed to fetch active images from blob storage: {str(e)}")
        return set()


def fetch_images_from_registry():
    try:
        # Registry API URL to list repositories
        registry_catalog_url = f"{REGISTRY_BASE_URL}/v2/_catalog?n=1000"
        response = requests.get(registry_catalog_url, auth=(REGISTRY_USER, REGISTRY_PASSWORD))

        if response.status_code != 200:
            log_error(f"Failed to fetch images from registry. Status code: {response.status_code}")
            return []

        # Parse the registry catalog response
        repositories = response.json().get("repositories", [])
        if not repositories:  # Handle case where 'repositories' is None or empty
            print("No repositories found in the registry.")
            return []

        images = []

        # For each repository, get tags
        for repo in repositories:
                tags_url = f"{REGISTRY_BASE_URL}/v2/{repo}/tags/list"
                tag_response = requests.get(tags_url, auth=(REGISTRY_USER, REGISTRY_PASSWORD))
                if tag_response.status_code == 200:
                    tags = tag_response.json().get("tags", [])
                    if not tags:  # Handle case where 'tags' is None or empty
                        print(f"No tags found for repository {repo}.")
                    else:
                        for tag in tags:
                            images.append(f"{repo}:{tag}")
                else:
                    log_error(f"Failed to fetch tags for repository {repo}. Status code: {tag_response.status_code}")
        return images
    except Exception as e:
        log_error(f"Failed to fetch registry images: {str(e)}")
        return []


# Delete unused images from the Docker registry
# def delete_image_from_registry(image):
#     try:
#         repo, tag = image.split(":")
#         # Get the manifest for the image tag
#         manifest_url = f"{REGISTRY_BASE_URL}/v2/{repo}/manifests/{tag}"
#         headers = {"Accept": "application/vnd.docker.distribution.manifest.v2+json"}
#         manifest_response = requests.get(manifest_url, auth=(REGISTRY_USER, REGISTRY_PASSWORD), headers=headers)

#         if manifest_response.status_code != 200:
#             log_error(f"Failed to fetch manifest for {image}. Status code: {manifest_response.status_code}")
#             return

#         # Extract the image digest from the manifest
#         manifest_data = manifest_response.json() # can be utilized later
#         image_digest = manifest_response.headers['Docker-Content-Digest']

#         # Dry run check
#         if DELETE_DRY_RUN:
#             print(f"[DRY RUN] Would delete image: {image}")
#             return

#         # Perform the deletion using the digest
#         delete_url = f"{REGISTRY_BASE_URL}/v2/{repo}/manifests/{image_digest}"
#         delete_response = requests.delete(delete_url, auth=(REGISTRY_USER, REGISTRY_PASSWORD))

#         if delete_response.status_code == 202:
#             print(f"Successfully deleted image: {image}")
#         else:
#             log_error(f"Failed to delete image {image}. Status code: {delete_response.status_code}")
#     except Exception as e:
#         log_error(f"Error deleting image {image}: {str(e)}")


def write_unused_images_to_file(images_to_delete, file_path="images_to_delete.txt"):
    try:
        with open(file_path, "w") as file:
            for image in images_to_delete:
                file.write(f"{image}\n")
        print(f"Unused images written to {file_path}")
    except Exception as e:
        log_error(f"Failed to write unused images to file: {e}")

def write_active_images_to_file(active_images, file_path="active_images_blob.txt"):
    try:
        with open(file_path, "w") as file:
            for image in active_images:
                file.write(f"{image}\n")
        print(f"Active images fetched form blob written to file: {file_path}")
    except Exception as e:
        log_error(f"Failed to write active images to file: {e}")


def main():

    active_images = fetch_active_images_from_blob()

    # remove registry.<domin name>.com/ prefix from fetched images
    prefix = "registry.<domin name>.com/"
    active_images = {image[len(prefix):] if image.startswith(prefix) else image for image in active_images}


    if not active_images:
        log_error("No active images found. Aborting cleanup.")
        return

    write_active_images_to_file(active_images)

    # Fetch all images in the registry
    registry_images = fetch_images_from_registry()
    if not registry_images:
        log_error("No images found in registry. Aborting cleanup.")
        return

    # Find unused images
    unused_images = set(registry_images) - active_images
    print(f"Found {len(unused_images)} unused images.")

    # Filter out reserved images from unused_images
    unused_images_to_delete = [image for image in unused_images if image not in static_images()]

    # Delete unused images
    # for image in unused_images_to_delete:
    #     delete_image_from_registry(image)

    write_unused_images_to_file(unused_images_to_delete)
    print("Cleanup job completed.")

if __name__ == '__main__':
    main()
