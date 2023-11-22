"""Functions to upload data to Zeno's backend."""
import io
import json
import re
import urllib
from importlib.metadata import version as package_version
from json import JSONDecodeError
from typing import Dict, List, Optional, Union
from urllib.parse import quote

import pandas as pd
import pkg_resources
import pyarrow as pa
import requests
import tqdm.auto as tqdm
from outdated import warn_if_outdated
from packaging import version
from pydantic import BaseModel

from zeno_client.exceptions import APIError, ClientVersionError
from zeno_client.util import df_to_pa

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
        *,
        id_column: str,
        data_column: Optional[str] = None,
        label_column: Optional[str] = None,
    ):
        """Upload a dataset to a Zeno project.

        Args:
            df (pd.DataFrame): The dataset to upload as a Pandas DataFrame.
            id_column (str): Column name containing unique instance IDs.
            data_column (str | None, optional): Column containing the
                instance data. This can be raw data for data types such as
                text, or URLs for large media data such as images and videos.
            label_column (str | None, optional): Column containing the
                instance labels. Defaults to None.
        """
        if (
            id_column == label_column
            or id_column == data_column
            or (
                label_column == data_column
                and label_column is not None
                and data_column is not None
            )
        ):
            raise ValueError(
                "ERROR: ID, data, and label column names must be unique."
                + " Please create a copy of your data_column"
                + " if you want to use it as id_column."
            )

        if id_column not in df.columns:
            raise ValueError("ERROR: id_column not found in dataframe")

        if data_column and data_column not in df.columns:
            raise ValueError("ERROR: data_column not found in dataframe")

        if label_column and label_column not in df.columns:
            raise ValueError("ERROR: label_column not found in dataframe")

        pa_table = df_to_pa(df, id_column)

        response = requests.post(
            f"{self.endpoint}/api/dataset-schema",
            data={
                "project_uuid": self.project_uuid,
                "id_column": id_column,
                "data_column": data_column,
                "label_column": label_column,
            },
            files={"file": (pa_table.schema.serialize().to_pybytes())},
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code != 200:
            _handle_error_response(response)

        # Rename columns to match UUIDs generated by backend
        column_names = response.json()
        pa_table = pa_table.rename_columns(column_names)

        # batches < 1MB, limit for spooling to memory in FastAPI
        batches = pa_table.to_batches(
            max_chunksize=900000 / pa_table.slice(0, 1).nbytes
        )
        for batch in tqdm.tqdm(batches):
            sink = io.BytesIO()
            with pa.ipc.new_file(sink, batch.schema) as writer:
                writer.write_batch(batch)

            sink.seek(0)
            response = requests.post(
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
        self, df: pd.DataFrame, *, name: str, id_column: str, output_column: str
    ):
        """Upload a system to a Zeno project.

        Args:
            df (pd.DataFrame): The dataset to upload.
            name (str): The name of the system to upload.
            id_column (str): The name of the column containing the instance IDs.
            output_column (str): The name of the column containing the system output.
        """
        if name == "":
            raise ValueError("System name cannot be empty")
        if re.findall("[/]", name):
            raise ValueError("System name cannot contain a '/'.")

        if id_column == output_column:
            raise ValueError(
                "ERROR: column names must be unique."
                + " Please create a copy of your output_column"
                + " if you want to use it as id_column."
            )

        if id_column not in df.columns:
            raise ValueError("ERROR: id_column not found in dataframe")

        if output_column not in df.columns:
            raise ValueError("ERROR: output_column not found in dataframe")

        pa_table = df_to_pa(df, id_column)

        response = requests.post(
            f"{self.endpoint}/api/system-schema",
            data={
                "project_uuid": self.project_uuid,
                "system_name": name,
                "id_column": id_column,
                "output_column": output_column,
            },
            files={"file": (pa_table.schema.serialize().to_pybytes())},
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code != 200:
            _handle_error_response(response)

        column_names = response.json()
        pa_table = pa_table.rename_columns(column_names)

        # batches < 1MB, limit for spooling to memory in FastAPI
        batches = pa_table.to_batches(
            max_chunksize=900000 / pa_table.slice(0, 1).nbytes
        )
        for batch in tqdm.tqdm(batches):
            sink = io.BytesIO()
            with pa.ipc.new_file(sink, batch.schema) as writer:
                writer.write_batch(batch)

            sink.seek(0)
            name = quote(name, safe="!~*'()")
            response = requests.post(
                f"{self.endpoint}/api/system/{self.project_uuid}/{name}",
                files={"file": (sink)},
                headers={
                    "Authorization": "Bearer " + self.api_key,
                },
                verify=True,
            )
            if response.status_code != 200:
                _handle_error_response(response)

        print("Successfully uploaded system")

    def delete_system(self, name: str):
        """Delete a system from a Zeno project.

        Args:
            name (str): The name of the system to delete.
        """
        if name == "":
            raise ValueError("System name cannot be empty")

        name = quote(name, safe="!~*'()")
        response = requests.delete(
            f"{self.endpoint}/api/system/{self.project_uuid}/{name}",
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code != 200:
            _handle_error_response(response)

        print("Successfully deleted system")

    def delete_all_systems(self):
        """Delete all systems from a Zeno project."""
        response = requests.delete(
            f"{self.endpoint}/api/systems/{self.project_uuid}",
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code != 200:
            _handle_error_response(response)

        print("Successfully deleted all systems")


class ZenoClient:
    """Client class for data upload functionality to Zeno."""

    api_key: str
    endpoint: str

    def __init__(self, api_key: str, *, endpoint: str = DEFAULT_BACKEND) -> None:
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

        warn_if_outdated(
            "zeno-client", pkg_resources.get_distribution("zeno-client").version
        )

        self.api_key = api_key
        self.endpoint = endpoint

    def create_project(
        self,
        *,
        name: str,
        view: Union[str, Dict] = "",
        description: str = "",
        metrics: List[ZenoMetric] = [],
        samples_per_page: int = 10,
        public: bool = False,
    ) -> ZenoProject:
        """Creates an empty project in Zeno's backend.

        Args:
            name (str): The name of the project to be created. The project will be
                created under the current user, e.g. username/name.
            view (Union[str, Dict], optional): The view to use for the project.
                Defaults to "".
            description (str, optional): The description of the project. Defaults to "".
            metrics (list[ZenoMetric], optional): The metrics to calculate for the
                project. Defaults to [].
            samples_per_page (int, optional): The number of samples to show per page.
                Defaults to 10.
            public (bool, optional): Whether the project is public. Defaults to False.

        Returns:
            ZenoProject | None: The created project object or None if the project could
                not be created.

        Raises:
            ValidationError: If the config does not match the ProjectConfig schema.
            APIError: If the project could not be created.
        """
        if name == "":
            raise ValueError("Project name cannot be empty")

        if re.findall("[/]", name):
            raise ValueError("Project name cannot contain a '/'.")

        # if view is dict, dump to json
        if isinstance(view, dict):
            view = json.dumps(view)

        response = requests.post(
            f"{self.endpoint}/api/project",
            json={
                "uuid": "",
                "name": name,
                "view": view,
                "metrics": [dict(m) for m in metrics],
                "owner_name": "",
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
            print("Successfully created project.")
        elif response.status_code == 200:
            response = response.json()
            print("Successfully updated project.")
        else:
            _handle_error_response(response)
        print(
            "Access your project at ",
            zeno_hub
            + "/project/"
            + urllib.parse.quote(response["uuid"])
            + "/"
            + urllib.parse.quote(name),
        )
        return ZenoProject(self.api_key, response["uuid"], self.endpoint)

    def get_project(self, owner_name: str, project_name: str) -> ZenoProject:
        """Get a project object by its owner and name.

        Args:
            owner_name (str): The owner of the project to get.
            project_name (str): The name of the project to get.

        Returns:
            Project: The project object.

        Raises:
            APIError: If the project could not be found.
        """
        user = quote(owner_name, safe="!~*'()")
        project = quote(project_name, safe="!~*'()")
        response = requests.get(
            f"{self.endpoint}/api/project-uuid/{user}/{project}",
            headers={"Authorization": "Bearer " + self.api_key},
            verify=True,
        )
        if response.status_code == 200:
            return ZenoProject(self.api_key, response.text[1:-1], self.endpoint)
        else:
            _handle_error_response(response)
