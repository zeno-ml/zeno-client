"""Functions to upload data to Zeno's backend."""
import io
from importlib.metadata import version as package_version
from json import JSONDecodeError
from typing import List, Optional

import pandas as pd
import pyarrow as pa
import requests
import tqdm.auto as tqdm
from packaging import version
from pydantic import BaseModel

from zeno_client.exceptions import APIError, ClientVersionError

DEFAULT_BACKEND = "https://api.zenoml.com"


def _handle_error_response(response: requests.Response):
    try:
        raise APIError(response.json()["detail"], response.status_code)
    except JSONDecodeError:
        raise APIError(response.text, response.status_code)


class ZenoMetric(BaseModel):
    """A metric to calculate for a Zeno project.

    Attributes:
        id (int): The ID of the metric. -1 if not set.
        name (str): The name of the metric.
        type (str): The type of metric to calculate. Currently only "mean".
        columns (list[str]): The columns to calculate the metric on.
            Empty list if not set.
    """

    id: int = -1
    name: str
    type: str
    columns: List[str] = []


class ZenoProject:
    """Provides data upload functionality for a Zeno project.

    Should NOT be initialized directly, but rather through the ZenoClient.
    """

    api_key: str
    project_uuid: str
    endpoint: str

    def __init__(
        self, api_key: str, project_uuid: str, endpoint: str = DEFAULT_BACKEND
    ):
        """Initialize the Project object for API upload calls.

        Args:
            api_key (str): the API key to authenticate uploads with.
            project_uuid (str): the ID of the project to add data to.
            endpoint (str, optional): the base URL of the Zeno backend.
        """
        self.api_key = api_key
        self.project_uuid = project_uuid
        self.endpoint = endpoint

    def upload_dataset(
        self,
        df: pd.DataFrame,
        id_column: str,
        label_column: Optional[str] = "",
        data_column: Optional[str] = "",
        url_column: Optional[str] = "",
    ):
        """Upload a dataset to a Zeno project.

        Args:
            df (pd.DataFrame): The dataset to upload.
            id_column (str): The name of the column containing the instance IDs.
                These can either be unique IDs, URLs to hosted data, or URL parts in
                combination with a project's endpoint.
            label_column (str | None, optional): The name of the column containing the
                instance labels. Defaults to None.
            data_column (str | None, optional): The name of the column containing the
                raw data. Only works for small text data. Defaults to None.
        """
        if len(id_column) == 0:
            raise ValueError("ERROR: id_column name must be non-empty")

        pa_table = pa.Table.from_pandas(df)

        response = requests.post(
            f"{self.endpoint}/api/dataset-schema",
            json={
                "project_uuid": self.project_uuid,
                "columns": pa_table.column_names,
                "id_column": id_column,
                "label_column": label_column,
                "data_column": data_column,
                "url_column": url_column,
            },
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )

        column_names = response.json()
        pa_table = pa_table.rename_columns(column_names)

        # batches < 1MB, limit for spooling to memory in FastAPI
        batches = pa_table.to_batches(
            max_chunksize=1000000 / pa_table.slice(0, 1).nbytes
        )
        for batch in tqdm.tqdm(batches):
            sink = io.BytesIO()
            with pa.ipc.new_file(sink, batch.schema) as writer:
                writer.write_batch(batch)

            sink.seek(0)
            requests.post(
                f"{self.endpoint}/api/dataset/{self.project_uuid}",
                files={"file": (sink)},
                headers={
                    "Authorization": "Bearer " + self.api_key,
                },
                verify=True,
            )
            if response.status_code != 200:
                _handle_error_response(response)

        print("Successfully uploaded data")

    def upload_system(
        self, name: str, df: pd.DataFrame, id_column: str, output_column: str
    ):
        """Upload a system to a Zeno project.

        Args:
            name (str): The name of the system to upload.
            df (pd.DataFrame): The dataset to upload.
            output_column (str): The name of the column containing the system output.
            id_column (str): The name of the column containing the instance IDs.
        """
        if len(name) == 0 or len(output_column) == 0:
            raise ValueError("System_name and output_column must be non-empty.")

        b = io.BytesIO()
        df.to_feather(b)
        b.seek(0)
        response = requests.post(
            f"{self.endpoint}/api/system/{self.project_uuid}",
            data={
                "system_name": name,
                "output_column": output_column,
                "id_column": id_column,
            },
            files={"file": (b)},
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code == 200:
            print("Successfully uploaded system")
        else:
            _handle_error_response(response)


class ZenoClient:
    """Client class for data upload functionality to Zeno."""

    api_key: str
    endpoint: str

    def __init__(self, api_key, endpoint=DEFAULT_BACKEND) -> None:
        """Initialize the ZenoClient object for API upload calls.

        Args:
            api_key (str): the API key to authenticate uploads with.
            endpoint (str, optional): the base URL of the Zeno backend.
                Defaults to DEFAULT_BACKEND.
        """
        response = requests.get(
            endpoint + "/api/min-client-version",
            headers={"Authorization": "Bearer " + api_key},
            verify=True,
        )
        if response.status_code == 200:
            response = response.text.replace('"', "")
            if version.parse(response) > version.parse(package_version("zeno-client")):
                raise ClientVersionError(
                    f"Please upgrade your zeno-client package to version {response} or "
                    "higher"
                )
        else:
            _handle_error_response(response)

        self.api_key = api_key
        self.endpoint = endpoint

    def create_project(
        self,
        name: str,
        view: str,
        metrics: List[ZenoMetric] = [],
        data_url: str = "",
        calculate_histogram_metrics: bool = True,
        samples_per_page: int = 10,
        public: bool = False,
        description: str = "",
    ) -> ZenoProject:
        """Creates an empty project in Zeno's backend.

        Args:
            name (str): The name of the project to be created. The project will be
                created under the current user, e.g. username/name.
                project: str,
            view (str): The view to use for the project.
            metrics (list[ZenoMetric], optional): The metrics to calculate for the
                project. Defaults to [].
            data_url (str, optional): The base URL to load datapoints from.
                Defaults to "".
            calculate_histogram_metrics (bool, optional): Whether to calculate histogram
                metrics. Defaults to True.
            samples_per_page (int, optional): The number of samples to show per page.
                Defaults to 10.
            public (bool, optional): Whether the project is public. Defaults to False.
            description (str, optional): The description of the project. Defaults to "".

        Returns:
            ZenoProject | None: The created project object or None if the project could
                not be created.

        Raises:
            ValidationError: If the config does not match the ProjectConfig schema.
            APIError: If the project could not be created.
        """
        response = requests.post(
            f"{self.endpoint}/api/project",
            json={
                "uuid": "",
                "name": name,
                "view": view,
                "metrics": [dict(m) for m in metrics],
                "owner_name": "",
                "data_url": data_url,
                "calculate_histogram_metrics": calculate_histogram_metrics,
                "samplesPerPage": samples_per_page,
                "public": public,
                "editor": True,
                "description": description,
            },
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )

        zeno_hub = "[YOUR ZENO HUB URL]"
        if self.endpoint == DEFAULT_BACKEND:
            zeno_hub = "https://hub.zenoml.com"

        if response.status_code == 201:
            response = response.json()
            print("Successfully created project ", response["uuid"])
            print(
                "To access your project, go to ",
                zeno_hub + "/project/" + response["ownerName"] + "/" + response["name"],
            )
            return ZenoProject(self.api_key, response["uuid"], self.endpoint)
        elif response.status_code == 200:
            response = response.json()
            print("Successfully updated project ", response["uuid"])
            print(
                "To access your project, go to ",
                zeno_hub + "/project/" + response["ownerName"] + "/" + response["name"],
            )
            return ZenoProject(self.api_key, response["uuid"], self.endpoint)
        else:
            _handle_error_response(response)

    def get_project(self, project_name: str) -> ZenoProject:
        """Get a project object by its name. Names are split into owner/project_name.

        Args:
            project_name (str): The owner/project_name of the project to get.

        Returns:
            Project | None: The project object or None if the project could not be
                found.

        Raises:
            APIError: If the project could not be found.
        """
        # Get owner and project name from project_name.
        # If no owner, assume current user.
        split_project_name = project_name.split("/")
        if len(split_project_name) == 1:
            raise Exception("Project name must be in the format owner/project_name")
        else:
            user = split_project_name[0]
            project_name = split_project_name[1]

        response = requests.get(
            f"{self.endpoint}/api/project-uuid/{user}/{project_name}",
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code == 200:
            return ZenoProject(self.api_key, response.text[1:-1], self.endpoint)
        else:
            _handle_error_response(response)
