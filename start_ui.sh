#!/bin/bash
set -e

echo "Starting Smart Travel Planner UI..."
uv run streamlit run app.py --server.port 8501
