"""Functions to upload data to Zeno's backend."""
import io
from typing import List, Optional

import pandas as pd
import requests
from pydantic import BaseModel

DEFAULT_BACKEND = "https://api.hub.zenoml.com"


class ZenoMetric(BaseModel):
    """A metric to calculate for a Zeno project.

    Attributes:
        id (int): The ID of the metric. -1 if not set.
        name (str): The name of the metric.
        type (str): The type of metric to calculate.
        columns (list[str]): The columns to calculate the metric on.
    """

    id: int = -1
    name: str
    type: str
    columns: List[str]


class ZenoProject:
    """Provides data upload functionality for a Zeno project.

    Attributes:
        api_key (str): The API key to authenticate uploads with.
        project_uuid (str): The ID of the project to add data to.
        endpoint (str): The base URL of the Zeno backend.
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
        label_column: Optional[str] = None,
        data_column: Optional[str] = None,
    ):
        """Upload a dataset to a Zeno project.

        Args:
            df (pd.DataFrame): The dataset to upload.
            id_column (str): The name of the column containing the instance IDs.
            label_column (str | None, optional): The name of the column containing the
                instance labels. Defaults to None.
            data_column (str | None, optional): The name of the column containing the
                raw data. Only works for small text data. Defaults to None.
        """
        if len(id_column) == 0:
            raise Exception("ERROR: id_column name must be non-empty")

        b = io.BytesIO()
        df.to_feather(b)
        b.seek(0)
        response = requests.post(
            f"{self.endpoint}/api/dataset/{self.project_uuid}",
            data={
                "id_column": id_column,
                "label_column": label_column if label_column is not None else "",
                "data_column": data_column if data_column is not None else "",
            },
            files={"file": (b)},
            headers={"Authorization": "Bearer " + self.api_key},
        )
        if response.status_code == 200:
            print("Successfully uploaded data")
        else:
            raise Exception(response.json()["detail"])

    def upload_system(
        self, system_name: str, df: pd.DataFrame, output_column: str, id_column: str
    ):
        """Upload a system to a Zeno project.

        Args:
            df (pd.DataFrame): The dataset to upload.
            system_name (str): The name of the system to upload.
            output_column (str): The name of the column containing the system output.
            id_column (str): The name of the column containing the instance IDs.
        """
        if len(system_name) == 0 or len(output_column) == 0:
            raise Exception("System_name and output_column must be non-empty.")

        b = io.BytesIO()
        df.to_feather(b)
        b.seek(0)
        response = requests.post(
            f"{self.endpoint}/api/system/{self.project_uuid}",
            data={
                "system_name": system_name,
                "output_column": output_column,
                "id_column": id_column,
            },
            files={"file": (b)},
            headers={"Authorization": "Bearer " + self.api_key},
        )
        if response.status_code == 200:
            print("Successfully uploaded system")
        else:
            raise Exception(response.json()["detail"])


class ZenoClient:
    """Client class for data upload functionality to Zeno.

    Attributes:
        api_key (str): The API key to authenticate uploads with.
        endpoint (str): The base URL of the Zeno backend.
    """

    api_key: str
    endpoint: str

    def __init__(self, api_key, endpoint=DEFAULT_BACKEND) -> None:
        """Initialize the ZenoClient object for API upload calls.

        Args:
            api_key (str): the API key to authenticate uploads with.
            endpoint (str, optional): the base URL of the Zeno backend.
                Defaults to DEFAULT_BACKEND.
        """
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
        public: bool = True,
    ) -> ZenoProject:
        """Creates an empty project in Zeno's backend.

        Args:
            name (str): The name of the project to be created. The project will be
                created under the current user, e.g. username/name.
                project: str,
            view (str): The view to use for the project.
            metrics (list[ZenoMetric], optional): The metrics to calculate for the
                project. Defaults to [].
            data_url (str, optional): The URL to the data to use for the project.
                Defaults to "".
            calculate_histogram_metrics (bool, optional): Whether to calculate histogram
                metrics. Defaults to True.
            samples_per_page (int, optional): The number of samples to show per page.
                Defaults to 10.
            public (bool, optional): Whether the project is public. Defaults to False.


        Returns:
            ZenoProject | None: The created project object or None if the project could
                not be created.

        Raises:
            ValidationError: If the config does not match the ProjectConfig schema.
            HTTPError: If the project could not be created.
        """
        response = requests.post(
            f"{self.endpoint}/api/project",
            json={
                "uuid": "",
                "name": name,
                "view": view,
                "metrics": [m.model_dump() for m in metrics],
                "owner_name": "",
                "data_url": data_url,
                "calculate_histogram_metrics": calculate_histogram_metrics,
                "samplesPerPage": samples_per_page,
                "public": public,
                "editor": True,
            },
            headers={"Authorization": "Bearer " + self.api_key},
        )
        if response.status_code == 200:
            print("Successfully created project ", response.text[1:-1])
            return ZenoProject(self.api_key, response.text[1:-1], self.endpoint)
        else:
            raise Exception(response.json()["detail"])

    def get_project(self, project_name: str) -> ZenoProject:
        """Get a project object by its name. Names are split into owner/project_name.

        Args:
            project_name (str): The owner/project_name of the project to get.

        Returns:
            Project | None: The project object or None if the project could not be
                found.


        Raises:
            HTTPError: If the project could not be found.
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
        )
        if response.status_code == 200:
            return ZenoProject(self.api_key, response.text[1:-1], self.endpoint)
        else:
            raise Exception(response.json()["detail"])
