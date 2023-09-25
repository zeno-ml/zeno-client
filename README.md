# Zeno Python Client

The Zeno Python client lets you create and manage Zeno projects from Python.

## Example

A Zeno project has a base `dataset` and any number of `systems` (AI models) to evaluate on a dataset.
The following example shows how to upload a dataset and a system to a Zeno project.

```python
from zeno_client import ZenoClient
import pandas as pd

# Create a Zeno client with your API key
client = ZenoClient("YOUR_API_KEY")

# Create a project with a specific data renderer, e.g. "text-classification" or "image-classification"
# See view options at https://zenoml.com/docs/views/
project = client.create_project("my_project", "text-classification")

# Upload a simple dataset
# You need to provide at least an id column.
# Your dataframe can contain additional metadata which will be usable in Zeno.
df = pd.DataFrame({
    "id": [1, 2, 3],
    "text": ["Zeno", "of", "Elea"],
    "label": ["A", "B", "B"]
})
project.upload_dataset(df, id_column="id", label_column="label", data_column="text")

# Upload a system to the project
# ... run inference on your model ...
df = pd.DataFrame({"id": [1, 2, 3], "output": ["A", "B", "A"]})
project.upload_system("my_system", df, output_column="output", id_column="id")
```

See the [examples](./examples) directory for more in-depth examples.

## API Documentation

Documentation generated with [pydoc-markdown](https://niklasrosenstein.github.io/pydoc-markdown/).

`pydoc-markdown -I zeno_client -m client --render-toc > docs.md`

# Table of Contents

- [client](#client)
  - [ZenoMetric](#client.ZenoMetric)
  - [ZenoProject](#client.ZenoProject)
    - [\_\_init\_\_](#client.ZenoProject.__init__)
    - [upload_dataset](#client.ZenoProject.upload_dataset)
    - [upload_system](#client.ZenoProject.upload_system)
  - [ZenoClient](#client.ZenoClient)
    - [\_\_init\_\_](#client.ZenoClient.__init__)
    - [create_project](#client.ZenoClient.create_project)
    - [get_project](#client.ZenoClient.get_project)

<a id="client"></a>

# client

Functions to upload data to Zeno's backend.

<a id="client.ZenoMetric"></a>

## ZenoMetric Objects

```python
class ZenoMetric(BaseModel)
```

A metric to calculate for a Zeno project.

**Attributes**:

- `id` _int_ - The ID of the metric. -1 if not set.
- `name` _str_ - The name of the metric.
- `type` _str_ - The type of metric to calculate.
- `columns` _list[str]_ - The columns to calculate the metric on.

<a id="client.ZenoProject"></a>

## ZenoProject Objects

```python
class ZenoProject()
```

Provides data upload functionality for a Zeno project.

**Attributes**:

- `api_key` _str_ - The API key to authenticate uploads with.
- `project_uuid` _str_ - The ID of the project to add data to.
- `endpoint` _str_ - The base URL of the Zeno backend.

<a id="client.ZenoProject.__init__"></a>

#### \_\_init\_\_

```python
def __init__(api_key: str, project_uuid: str, endpoint: str = DEFAULT_BACKEND)
```

Initialize the Project object for API upload calls.

**Arguments**:

- `api_key` _str_ - the API key to authenticate uploads with.
- `project_uuid` _str_ - the ID of the project to add data to.
- `endpoint` _str, optional_ - the base URL of the Zeno backend.

<a id="client.ZenoProject.upload_dataset"></a>

#### upload_dataset

```python
def upload_dataset(df: pd.DataFrame,
                   id_column: str,
                   label_column: Optional[str] = None,
                   data_column: Optional[str] = None)
```

Upload a dataset to a Zeno project.

**Arguments**:

- `df` _pd.DataFrame_ - The dataset to upload.
- `id_column` _str_ - The name of the column containing the instance IDs.
- `label_column` _str | None, optional_ - The name of the column containing the
  instance labels. Defaults to None.
- `data_column` _str | None, optional_ - The name of the column containing the
  raw data. Only works for small text data. Defaults to None.

<a id="client.ZenoProject.upload_system"></a>

#### upload_system

```python
def upload_system(system_name: str, df: pd.DataFrame, output_column: str,
                  id_column: str)
```

Upload a system to a Zeno project.

**Arguments**:

- `df` _pd.DataFrame_ - The dataset to upload.
- `system_name` _str_ - The name of the system to upload.
- `output_column` _str_ - The name of the column containing the system output.
- `id_column` _str_ - The name of the column containing the instance IDs.

<a id="client.ZenoClient"></a>

## ZenoClient Objects

```python
class ZenoClient()
```

Client class for data upload functionality to Zeno.

**Attributes**:

- `api_key` _str_ - The API key to authenticate uploads with.
- `endpoint` _str_ - The base URL of the Zeno backend.

<a id="client.ZenoClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(api_key, endpoint=DEFAULT_BACKEND) -> None
```

Initialize the ZenoClient object for API upload calls.

**Arguments**:

- `api_key` _str_ - the API key to authenticate uploads with.
- `endpoint` _str, optional_ - the base URL of the Zeno backend.
  Defaults to DEFAULT_BACKEND.

<a id="client.ZenoClient.create_project"></a>

#### create_project

```python
def create_project(name: str,
                   view: str,
                   metrics: List[ZenoMetric] = [],
                   data_url: str = "",
                   calculate_histogram_metrics: bool = True,
                   samples_per_page: int = 10,
                   public: bool = True) -> ZenoProject
```

Creates an empty project in Zeno's backend.

**Arguments**:

- `name` _str_ - The name of the project to be created. The project will be
  created under the current user, e.g. username/name.
- `project` - str,
- `view` _str_ - The view to use for the project.
- `metrics` _list[ZenoMetric], optional_ - The metrics to calculate for the
  project. Defaults to [].
- `data_url` _str, optional_ - The URL to the data to use for the project.
  Defaults to "".
- `calculate_histogram_metrics` _bool, optional_ - Whether to calculate histogram
  metrics. Defaults to True.
- `samples_per_page` _int, optional_ - The number of samples to show per page.
  Defaults to 10.
- `public` _bool, optional_ - Whether the project is public. Defaults to False.

**Returns**:

ZenoProject | None: The created project object or None if the project could
not be created.

**Raises**:

- `ValidationError` - If the config does not match the ProjectConfig schema.
- `HTTPError` - If the project could not be created.

<a id="client.ZenoClient.get_project"></a>

#### get_project

```python
def get_project(project_name: str) -> ZenoProject
```

Get a project object by its name. Names are split into owner/project_name.

**Arguments**:

- `project_name` _str_ - The owner/project_name of the project to get.

**Returns**:

Project | None: The project object or None if the project could not be
found.

**Raises**:

- `HTTPError` - If the project could not be found.
