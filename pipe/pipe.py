import yaml
import requests
from requests.auth import HTTPBasicAuth

from bitbucket_pipes_toolkit import Pipe
import os
import hashlib


BITBUCKET_API_REPOSITORY_URL = "https://api.bitbucket.org/2.0/repositories"
CLONE_DIR = os.getenv("BITBUCKET_CLONE_DIR")
CACHE_CHECKSUM_DIR = f"{CLONE_DIR}/.cache_checksum"

schema = {
    "BITBUCKET_USERNAME": {"required": True, "type": "string"},
    "BITBUCKET_APP_PASSWORD": {"required": True, "type": "string"},
    # NOTE: overridden global variable BITBUCKET_WORKSPACE will not be taken into account
    "WORKSPACE": {
        "required": False,
        "type": "string",
        "default": os.getenv("BITBUCKET_WORKSPACE"),
    },
    "REPO_SLUG": {
        "required": False,
        "type": "string",
        "default": os.getenv("BITBUCKET_REPO_SLUG"),
    },
    "CACHES": {"required": False, "type": "list", "default": []},
    "CHECKSUM_FILES": {"required": False, "type": "list", "default": []},
}

with open("/usr/bin/pipe.yml", "r") as metadata_file:
    metadata = yaml.safe_load(metadata_file.read())

pipe = Pipe(pipe_metadata=metadata, schema=schema, check_for_newer_version=True)


def run_pipe():
    pipe.log_info("Executing the pipe...")

    if os.path.exists(CACHE_CHECKSUM_DIR):
        CHECKS = []
        for file_path in pipe.get_variable("CHECKSUM_FILES"):
            if os.path.exists(f"{CACHE_CHECKSUM_DIR}/{file_path}"):
                if os.path.exists(f"{CLONE_DIR}/{file_path}"):
                    old_checksum = open(f"{CACHE_CHECKSUM_DIR}/{file_path}", "r").read()
                    new_checksum = hashlib.md5(
                        open(f"{CLONE_DIR}/{file_path}", "rb").read()
                    ).hexdigest()

                    pipe.log_info(
                        f"file: {file_path}, old checksum: {old_checksum}, new checksum: {new_checksum}"
                    )
                    CHECKS.append(new_checksum == old_checksum)

        if len(CHECKS) > 0 and False not in CHECKS:
            pipe.success("File(s) not changed. Skipping...")
            return
    else:
        os.makedirs(CACHE_CHECKSUM_DIR)

    workspace = pipe.get_variable("WORKSPACE")
    repo_name = pipe.get_variable("REPO_SLUG")
    bitbucket_user = pipe.get_variable("BITBUCKET_USERNAME")
    bitbucket_password = pipe.get_variable("BITBUCKET_APP_PASSWORD")

    caches_to_clear = pipe.get_variable("CACHES")

    url = f"{BITBUCKET_API_REPOSITORY_URL}/{workspace}/{repo_name}/pipelines-config/caches/?page=1&pagelen=100"
    auth = HTTPBasicAuth(bitbucket_user, bitbucket_password)

    response = requests.get(url, auth=auth)
    if not response.ok:
        pipe.fail(
            f"Failed to retrieve caches: {response.status_code} {response.text} {response.request.url}"
        )
    pipe.log_debug(response.request.headers)
    pipe.log_debug(response.content)
    response_json = response.json()

    if not caches_to_clear:
        clear_all_caches(
            workspace=workspace,
            repo_name=repo_name,
            cache_list_json=response_json["values"],
            auth=auth,
        )
    else:
        clear_selected_caches(
            workspace=workspace,
            repo_name=repo_name,
            cache_list_json=response_json["values"],
            caches_to_clear=caches_to_clear,
            auth=auth,
        )

    for file_path in pipe.get_variable("CHECKSUM_FILES"):
        if os.path.exists(f"{CLONE_DIR}/{file_path}"):
            with open(f"{CACHE_CHECKSUM_DIR}/{file_path}", "w") as f:
                new_checksum = hashlib.md5(
                    open(f"{CLONE_DIR}/{file_path}", "rb").read()
                ).hexdigest()
                f.write(new_checksum)
                pipe.log_info(f"Caching {file_path}, checksum: {new_checksum}")

    pipe.success("Finished clearing caches")


def clear_all_caches(workspace, repo_name, cache_list_json, auth):
    pipe.success("Retrieved {} caches".format(len(cache_list_json)))
    if len(cache_list_json) == 0:
        pipe.log_warning("No caches were found!")
    for cache in cache_list_json:
        pipe.log_debug(cache)
        clear_cache_by_uuid(
            workspace=workspace,
            repo_name=repo_name,
            cacheUuid=cache["uuid"],
            cache_name=cache["name"],
            auth=auth,
        )


def clear_selected_caches(workspace, repo_name, cache_list_json, caches_to_clear, auth):
    for cache in cache_list_json:
        pipe.log_debug(cache)
        if cache["name"] in caches_to_clear:
            clear_cache_by_uuid(
                workspace=workspace,
                repo_name=repo_name,
                cacheUuid=cache["uuid"],
                cache_name=cache["name"],
                auth=auth,
            )


def clear_cache_by_uuid(workspace, repo_name, cacheUuid, cache_name, auth):
    delete_url = f"{BITBUCKET_API_REPOSITORY_URL}/{workspace}/{repo_name}/pipelines-config/caches/{cacheUuid}"
    delete_response = requests.delete(delete_url, auth=auth)

    if delete_response.ok:
        pipe.success("Successfully cleared cache {}".format(cache_name))
    else:
        pipe.fail(f"Failed to clear cache {cache_name}: {delete_response.text}")


if __name__ == "__main__":
    run_pipe()
