# NewsXAI

A Prefect-powered pipeline for extracting and summarizing news articles using AI.

## Overview

NewsXAI combines the power of Prefect workflows with ControlFlow.ai to create an automated news extraction and summarization pipeline. The system:

1. Finds relevant news article URLs on a given topic
2. Extracts content from the articles
3. Summarizes and organizes the information
4. Presents a clean, formatted report

## Requirements

- Python 3.9+
- Prefect 3.x
- ControlFlow 0.6+
- OpenAI API key

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/navjots35/newsxai.git
   cd newsxai
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Register and create the OpenAI API key secret block:
   ```
   prefect block register -m prefect.blocks.system
   prefect block create --type secret --name openai-api-key
   ```
   When prompted, enter your OpenAI API key.

## Deployment

### Using GitHub Source

The project is configured to be deployed directly from GitHub. The `prefect.yaml` file includes configuration for pulling from the repository.

1. Make sure you have a work pool set up. If not, create one:
   ```
   prefect work-pool create thebh-dev --type process
   ```

2. Deploy the flow from the repository:
   ```
   prefect deploy
   ```

3. Start a worker to process flow runs:
   ```
   prefect worker start -p thebh-dev
   ```

### Running Locally

To test the flow locally:

```
python deployment.py
```

## Customization

To change the news topic or other parameters, edit the `prefect.yaml` file or provide parameters when running the flow:

```
prefect deployment run 'ControlFlow News Extraction Pipeline/default' -p news_topic="latest developments in quantum computing"
```

## Project Structure

- `flows/news.py`: Main implementation of the news extraction pipeline
- `deployment.py`: Deployment configuration
- `prefect.yaml`: Prefect deployment configuration
