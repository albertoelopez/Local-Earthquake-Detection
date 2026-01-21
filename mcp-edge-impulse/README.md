# Edge Impulse MCP Server

MCP server for integrating Edge Impulse with the earthquake alert data pipeline. Upload Kaggle earthquake data directly to Edge Impulse for model training.

## Setup

### 1. Install dependencies

```bash
cd mcp-edge-impulse
pip install -e .
```

### 2. Get Edge Impulse API Key

1. Go to [Edge Impulse Studio](https://studio.edgeimpulse.com)
2. Create a new project (or use existing)
3. Go to **Dashboard** → **Keys**
4. Copy your API key

### 3. Set environment variable

```bash
export EDGE_IMPULSE_API_KEY="ei_xxxxxxxxxxxx"
```

## Configure Claude Code

Add to your `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "edge-impulse": {
      "command": "python",
      "args": ["/home/darthvader/AI_Projects/earthquake_alert/mcp-edge-impulse/server.py"],
      "env": {
        "EDGE_IMPULSE_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

Or add to project-level `.claude/settings.json`.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_projects` | List all Edge Impulse projects |
| `get_project_info` | Get details about a project |
| `upload_kaggle_data` | Process and upload LANL/STEAD/synthetic data |
| `upload_csv` | Upload CSV file directly |
| `get_data_summary` | View training/testing data counts |
| `start_training` | Start model training |
| `get_training_status` | Check training progress |
| `download_model` | Export TFLite/Arduino library for ESP32 |
| `generate_synthetic_data` | Create synthetic test data |

## Usage Examples

### Upload Kaggle LANL data

```
Use upload_kaggle_data with:
- project_id: "12345"
- data_path: "/path/to/data/lanl"
- dataset_type: "lanl"
- max_samples: 500
```

### Generate and upload synthetic data

```
1. Use generate_synthetic_data to create test CSV
2. Use upload_csv to upload to Edge Impulse
```

### Train and export model

```
1. Use start_training to begin
2. Use get_training_status to monitor
3. Use download_model with format "esp32" to export
```

## Data Flow

```
Kaggle Data (LANL/STEAD)
         ↓
   data_loader.py
         ↓
   feature_extraction.py
         ↓
   Edge Impulse MCP Server
         ↓
   Edge Impulse Studio (train)
         ↓
   TFLite Model → ESP32
```
