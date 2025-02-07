import requests
import registry.errors.unauthorized


class Client:

    def __init__(self, registry_host_base_url, username, password):
        self.auth = (username, password)
        self.base_url = "{host_with_port}/v2".format(host_with_port=registry_host_base_url)
        # Quick test to confirm any authentication problems
        print("Testing connectivity to registry. URL: {url}".format(url=self.base_url))

        session = requests.Session()
        session.auth = (username, password)

        response = session.get(self.base_url)
        if response.status_code == 404:
            print("The URL does not seem to be of a Registry. Or is an unsupported registrys")
        elif response.status_code == 401:
            print("Not Authorized.")
            raise registry.errors.unauthorized.UnAuthorizedException()
        else:
            print("Sucessfully authenticated to registry")
            self._session = session

    def get_repositories(self):
        url = "{base}/_catalog".format(base=self.base_url)
        response = self._session.get(url)
        response = response.json()
        return response["repositories"]


    def get_tags(self, repoName):
        url = "{base}/{repoName}/tags/list".format(base=self.base_url, repoName=repoName)
        response = self._session.get(url)
        status_code = response.status_code
        response = response.json()

        if "errors" in response and len(response["errors"])>0:
            print("Error in retrieving tags for repo {repo}. HTTP Status Code is {status_code}".format(repo=repoName, status_code=status_code))
            for err in response["errors"]:
                print("ErrorCode is {code}. ErrorMessage is {message}".format(code=err["code"], message=err["message"]))

        if "tags" in response and response["tags"] is not None:
            return response["tags"]
        else:
            return []

    def get_digest(self, repo, tag):
        url = "{base}/{name}/manifests/{tag}".format(base=self.base_url, name=repo, tag=tag)
        # print("About to get URL ", url)
        self._session
        response = self._session.head(url, headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"})
        # print(response.json())

        if 'Docker-Content-Digest' in response.headers:
            tag_digest = response.headers['Docker-Content-Digest']
            # print("Tag Digest is ", tag_digest)
        else:
            tag_digest = None
            # print("Tag digest is none")
        return tag_digest
    def untag_by_digest(self, repo, tag_digest_to_delete):
        url = "{base}/{name}/manifests/{tag}".format(base=self.base_url, name=repo, tag=tag_digest_to_delete)
        print("About to delete URL ", url)
        response = self._session.get(url)
        # response = self._session.delete(url)
        print(response.status_code)
        # print(response.text)

