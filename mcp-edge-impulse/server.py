#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

sys.path.insert(0, str(Path(__file__).parent.parent / "data-processing" / "scripts"))

server = Server("edge-impulse-mcp")

API_BASE = "https://studio.edgeimpulse.com/v1/api"
INGESTION_BASE = "https://ingestion.edgeimpulse.com/api"


def get_api_key() -> str:
    key = os.environ.get("EDGE_IMPULSE_API_KEY", "")
    if not key:
        raise ValueError("EDGE_IMPULSE_API_KEY environment variable not set")
    return key


def get_project_id() -> str:
    return os.environ.get("EDGE_IMPULSE_PROJECT_ID", "")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_projects",
            description="List all Edge Impulse projects for the authenticated user",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_project_info",
            description="Get detailed information about a specific project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="upload_kaggle_data",
            description="Process and upload Kaggle earthquake data to Edge Impulse",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    },
                    "data_path": {
                        "type": "string",
                        "description": "Path to Kaggle data directory (LANL or STEAD)"
                    },
                    "dataset_type": {
                        "type": "string",
                        "enum": ["lanl", "stead", "synthetic"],
                        "description": "Type of dataset to process"
                    },
                    "max_samples": {
                        "type": "integer",
                        "description": "Maximum number of samples to upload (default: 1000)",
                        "default": 1000
                    },
                    "category": {
                        "type": "string",
                        "enum": ["training", "testing"],
                        "description": "Data category (training or testing)",
                        "default": "training"
                    }
                },
                "required": ["project_id", "data_path", "dataset_type"]
            }
        ),
        Tool(
            name="upload_csv",
            description="Upload a CSV file directly to Edge Impulse",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    },
                    "csv_path": {
                        "type": "string",
                        "description": "Path to CSV file"
                    },
                    "label": {
                        "type": "string",
                        "description": "Label for the data samples"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["training", "testing"],
                        "default": "training"
                    }
                },
                "required": ["project_id", "csv_path", "label"]
            }
        ),
        Tool(
            name="get_data_summary",
            description="Get summary of data in an Edge Impulse project",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="start_training",
            description="Start model training in Edge Impulse",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="get_training_status",
            description="Check the status of model training",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    }
                },
                "required": ["project_id"]
            }
        ),
        Tool(
            name="download_model",
            description="Download trained model as TFLite or Arduino library",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "Edge Impulse project ID"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save the model"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["tflite", "arduino", "esp32"],
                        "description": "Model export format",
                        "default": "esp32"
                    }
                },
                "required": ["project_id", "output_path"]
            }
        ),
        Tool(
            name="generate_synthetic_data",
            description="Generate synthetic earthquake data for testing",
            inputSchema={
                "type": "object",
                "properties": {
                    "num_samples": {
                        "type": "integer",
                        "description": "Number of samples to generate",
                        "default": 100
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save generated CSV"
                    },
                    "include_noise": {
                        "type": "boolean",
                        "description": "Include noise-only samples",
                        "default": True
                    }
                },
                "required": ["output_path"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        api_key = get_api_key()
    except ValueError as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        if name == "list_projects":
            return await handle_list_projects(client, headers)

        elif name == "get_project_info":
            return await handle_get_project_info(client, headers, arguments["project_id"])

        elif name == "upload_kaggle_data":
            return await handle_upload_kaggle_data(client, headers, arguments)

        elif name == "upload_csv":
            return await handle_upload_csv(client, headers, arguments)

        elif name == "get_data_summary":
            return await handle_get_data_summary(client, headers, arguments["project_id"])

        elif name == "start_training":
            return await handle_start_training(client, headers, arguments["project_id"])

        elif name == "get_training_status":
            return await handle_get_training_status(client, headers, arguments["project_id"])

        elif name == "download_model":
            return await handle_download_model(client, headers, arguments)

        elif name == "generate_synthetic_data":
            return await handle_generate_synthetic_data(arguments)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def handle_list_projects(client: httpx.AsyncClient, headers: dict) -> list[TextContent]:
    response = await client.get(f"{API_BASE}/projects", headers=headers)

    if response.status_code != 200:
        return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]

    data = response.json()
    projects = data.get("projects", [])

    if not projects:
        return [TextContent(type="text", text="No projects found. Create one at https://studio.edgeimpulse.com")]

    result = "## Edge Impulse Projects\n\n"
    for proj in projects:
        result += f"- **{proj['name']}** (ID: {proj['id']})\n"
        result += f"  - Created: {proj.get('created', 'N/A')}\n"
        result += f"  - Samples: {proj.get('sampleCount', 0)}\n\n"

    return [TextContent(type="text", text=result)]


async def handle_get_project_info(client: httpx.AsyncClient, headers: dict, project_id: str) -> list[TextContent]:
    response = await client.get(f"{API_BASE}/{project_id}/info", headers=headers)

    if response.status_code != 200:
        return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]

    data = response.json()
    proj = data.get("project", {})

    result = f"## Project: {proj.get('name', 'Unknown')}\n\n"
    result += f"- **ID**: {project_id}\n"
    result += f"- **Description**: {proj.get('description', 'N/A')}\n"
    result += f"- **Label Type**: {proj.get('labelType', 'N/A')}\n"
    result += f"- **Sensor**: {proj.get('sensor', 'N/A')}\n"
    result += f"- **Frequency**: {proj.get('frequency', 'N/A')} Hz\n"

    return [TextContent(type="text", text=result)]


async def handle_upload_kaggle_data(client: httpx.AsyncClient, headers: dict, args: dict) -> list[TextContent]:
    project_id = args["project_id"]
    data_path = args["data_path"]
    dataset_type = args["dataset_type"]
    max_samples = args.get("max_samples", 1000)
    category = args.get("category", "training")

    try:
        if dataset_type == "lanl":
            from data_loader import LANLDataLoader
            loader = LANLDataLoader(data_path)
            X, y = loader.load(max_samples=max_samples)
        elif dataset_type == "stead":
            from data_loader import STEADDataLoader
            loader = STEADDataLoader(data_path)
            X, y = loader.load(max_samples=max_samples)
        elif dataset_type == "synthetic":
            from data_loader import SyntheticDataGenerator
            generator = SyntheticDataGenerator()
            X, y = generator.generate(n_samples=max_samples)
        else:
            return [TextContent(type="text", text=f"Unknown dataset type: {dataset_type}")]

        from feature_extraction import FeatureExtractor
        extractor = FeatureExtractor(sampling_rate=100)
        features = extractor.fit_transform(X)

        uploaded = 0
        errors = 0

        import time
        for i in range(len(features)):
            label = "earthquake" if y[i] == 1 else "noise"
            timestamp = int(time.time() * 1000)
            filename = f"{label}.{timestamp}.{i}.json"

            sample_data = {
                "protected": {"ver": "v1", "alg": "none"},
                "signature": "0",
                "payload": {
                    "device_name": "kaggle-import",
                    "device_type": f"earthquake-{dataset_type}",
                    "interval_ms": 10,
                    "sensors": [{"name": "accX", "units": "m/s2"},
                               {"name": "accY", "units": "m/s2"},
                               {"name": "accZ", "units": "m/s2"}],
                    "values": X[i].tolist() if hasattr(X[i], 'tolist') else list(X[i])
                }
            }

            ingestion_headers = {
                "x-api-key": headers["x-api-key"],
                "x-label": label,
                "x-file-name": filename,
                "Content-Type": "application/json"
            }

            response = await client.post(
                f"{INGESTION_BASE}/{category}/data",
                headers=ingestion_headers,
                json=sample_data
            )

            if response.status_code == 200:
                uploaded += 1
            else:
                errors += 1

            if (i + 1) % 100 == 0:
                await asyncio.sleep(1)

        result = f"## Upload Complete\n\n"
        result += f"- **Uploaded**: {uploaded} samples\n"
        result += f"- **Errors**: {errors}\n"
        result += f"- **Category**: {category}\n"
        result += f"- **Dataset**: {dataset_type}\n"

        return [TextContent(type="text", text=result)]

    except ImportError as e:
        return [TextContent(type="text", text=f"Error importing data pipeline: {str(e)}. Make sure data-processing scripts are available.")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error processing data: {str(e)}")]


async def handle_upload_csv(client: httpx.AsyncClient, headers: dict, args: dict) -> list[TextContent]:
    project_id = args["project_id"]
    csv_path = args["csv_path"]
    label = args["label"]
    category = args.get("category", "training")

    try:
        import time
        df = pd.read_csv(csv_path)

        uploaded = 0
        for idx, row in df.iterrows():
            values = row.values.tolist()
            timestamp = int(time.time() * 1000)
            filename = f"{label}.{timestamp}.{idx}.json"

            sample_data = {
                "protected": {"ver": "v1", "alg": "none"},
                "signature": "0",
                "payload": {
                    "device_name": "csv-import",
                    "device_type": "earthquake-sensor",
                    "interval_ms": 10,
                    "sensors": [{"name": f"col_{i}", "units": "raw"} for i in range(len(values))],
                    "values": [values]
                }
            }

            ingestion_headers = {
                "x-api-key": headers["x-api-key"],
                "x-label": label,
                "x-file-name": filename,
                "Content-Type": "application/json"
            }

            response = await client.post(
                f"{INGESTION_BASE}/{category}/data",
                headers=ingestion_headers,
                json=sample_data
            )

            if response.status_code == 200:
                uploaded += 1

        return [TextContent(type="text", text=f"Uploaded {uploaded} rows from {csv_path}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_data_summary(client: httpx.AsyncClient, headers: dict, project_id: str) -> list[TextContent]:
    response = await client.get(f"{API_BASE}/{project_id}/raw-data/count", headers=headers)

    if response.status_code != 200:
        return [TextContent(type="text", text=f"Error: {response.status_code}")]

    data = response.json()

    result = "## Data Summary\n\n"
    result += f"- **Training samples**: {data.get('training', 0)}\n"
    result += f"- **Testing samples**: {data.get('testing', 0)}\n"
    result += f"- **Total**: {data.get('total', 0)}\n"

    return [TextContent(type="text", text=result)]


async def handle_start_training(client: httpx.AsyncClient, headers: dict, project_id: str) -> list[TextContent]:
    response = await client.post(f"{API_BASE}/{project_id}/jobs/train", headers=headers)

    if response.status_code != 200:
        return [TextContent(type="text", text=f"Error starting training: {response.status_code}")]

    return [TextContent(type="text", text="Training started. Use get_training_status to monitor progress.")]


async def handle_get_training_status(client: httpx.AsyncClient, headers: dict, project_id: str) -> list[TextContent]:
    response = await client.get(f"{API_BASE}/{project_id}/jobs", headers=headers)

    if response.status_code != 200:
        return [TextContent(type="text", text=f"Error: {response.status_code}")]

    data = response.json()
    jobs = data.get("jobs", [])

    if not jobs:
        return [TextContent(type="text", text="No training jobs found")]

    latest = jobs[0]
    result = f"## Training Status\n\n"
    result += f"- **Job ID**: {latest.get('id')}\n"
    result += f"- **Status**: {latest.get('status')}\n"
    result += f"- **Progress**: {latest.get('progress', 0)}%\n"

    return [TextContent(type="text", text=result)]


async def handle_download_model(client: httpx.AsyncClient, headers: dict, args: dict) -> list[TextContent]:
    project_id = args["project_id"]
    output_path = args["output_path"]
    export_format = args.get("format", "esp32")

    format_map = {
        "tflite": "tflite-float32",
        "arduino": "arduino",
        "esp32": "arduino-esp32"
    }

    deploy_type = format_map.get(export_format, "arduino-esp32")

    response = await client.get(
        f"{API_BASE}/{project_id}/deployment/download",
        headers=headers,
        params={"type": deploy_type}
    )

    if response.status_code != 200:
        return [TextContent(type="text", text=f"Error downloading model: {response.status_code}")]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(response.content)

    return [TextContent(type="text", text=f"Model downloaded to {output_path}")]


async def handle_generate_synthetic_data(args: dict) -> list[TextContent]:
    num_samples = args.get("num_samples", 100)
    output_path = args["output_path"]
    include_noise = args.get("include_noise", True)

    np.random.seed(42)

    samples = []
    labels = []

    eq_count = num_samples // 2 if include_noise else num_samples
    noise_count = num_samples - eq_count

    for _ in range(eq_count):
        t = np.linspace(0, 1, 100)
        freq = np.random.uniform(1, 10)
        amplitude = np.random.uniform(0.1, 0.5)
        signal = amplitude * np.sin(2 * np.pi * freq * t) * np.exp(-2 * t)
        signal += np.random.normal(0, 0.02, len(t))
        samples.append(signal)
        labels.append("earthquake")

    for _ in range(noise_count):
        signal = np.random.normal(0, 0.02, 100)
        samples.append(signal)
        labels.append("noise")

    df = pd.DataFrame(samples)
    df["label"] = labels

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    return [TextContent(type="text", text=f"Generated {num_samples} samples saved to {output_path}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
