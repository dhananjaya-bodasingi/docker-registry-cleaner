
import os
from dotenv import find_dotenv, load_dotenv
from datetime import datetime, timezone
from kubernetes import client, config

from azure.storage.blob import BlobServiceClient

# globals
CONTAINER_NAME = "active-docker-images"

def main():

    load_dotenv()  # take environment variables from .env.

    configuration = client.Configuration()

    now = datetime.now(timezone.utc) # current date and time
    file_name = now.strftime("%Y-%m-%d_%H%M.txt")
    print("Writing to file name " + file_name)
    use_incluster_config = os.getenv("use_incluster_config", False)
    if use_incluster_config:
        config.load_incluster_config()
    else:
        config.load_kube_config("./kubeconfig-sb", "sandbox-eastus")

    v1 = client.CoreV1Api()
    ret = v1.list_pod_for_all_namespaces(watch=False)

    containers_list = []
    print("---------List of Docker Images being used - Start---------")
    for i in ret.items:
        for container in i.spec.containers:
            image_str = f"{container.image}\n"
            if image_str.startswith("registry.whatfix.com") and image_str not in containers_list:
                containers_list.append(image_str)
                print(image_str)
    print("---------List of Docker Images being used - End---------")
    print(f"Writing to file {file_name} - Start")
    with open(file_name, "w") as file:
        file.writelines(containers_list)
    print("Writing to file - End")

    # storage_account_name="stdockerregistryimages"
    default_blob_sas_url = ""

    blob_sas_url = os.getenv("blob_sas_url", default_blob_sas_url)
    # print("Using Blob SAS URL", blob_sas_url)

    unique_aks_id= os.getenv("unique_aks_id", "default")
    blob_service_client = BlobServiceClient(blob_sas_url)

    blob_url =  now.strftime("%Y-%m-%d/")  + unique_aks_id + "/" + now.strftime("%H%M/") + file_name

    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_url)
    with open(file=file_name, mode="rb") as data:
        blob_client.upload_blob(data)


if __name__ == '__main__':
    main()
