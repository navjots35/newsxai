#!/usr/bin/env python3
# deployment.py

from prefect import flow
# Import GitRepository for specifying the source code location
from prefect.runner.storage import GitRepository
from flows.news import controlflow_news_pipeline

# Define the entrypoint flow that will be called by Prefect
# This flow definition is simple, it just calls the main implementation
@flow(name="ControlFlow News Extraction Pipeline")
def news_extraction_flow(
    news_topic: str = "recent advancements in AI safety research",
    azure_openai_api_key_block_name: str = "azure-openai-api-key",
    azure_openai_endpoint_block_name: str = "azure-openai-endpoint",
    azure_openai_deployment_block_name: str = "azure-openai-deployment",
    azure_openai_api_version_block_name: str = "azure-openai-api-version"
):
    """
    Entrypoint flow for Prefect deployments.
    Calls the main news extraction pipeline.
    """
    return controlflow_news_pipeline(
        news_topic=news_topic,
        azure_openai_api_key_block_name=azure_openai_api_key_block_name,
        azure_openai_endpoint_block_name=azure_openai_endpoint_block_name,
        azure_openai_deployment_block_name=azure_openai_deployment_block_name,
        azure_openai_api_version_block_name=azure_openai_api_version_block_name
    )

# This section now defines and creates the deployment when the script is run
if __name__ == "__main__":
    # Define the source code storage using GitRepository
    # Pointing to your public GitHub repo and the 'main' branch
    github_storage = GitRepository(
        url="https://github.com/navjots35/newsxai.git",
        branch="main"
        # No credentials needed for a public repository
    )

    # Define and create the deployment using flow.from_source().deploy()
    deployment = news_extraction_flow.from_source(
        source=github_storage,
        # The entrypoint is this script and the flow function defined above
        entrypoint="deployment.py:news_extraction_flow"
    ).deploy(
        name="newsxai", # Deployment name
        work_pool_name="thebh-dev", # Specify your work pool
        tags=["controlflow", "news", "llm", "github"],
        # Define default parameters for the deployment runs
        parameters={
            "news_topic": "recent advancements in stock market",
            "azure_openai_api_key_block_name": "azure-openai-api-key",
            "azure_openai_endpoint_block_name": "azure-openai-endpoint",
            "azure_openai_deployment_block_name": "azure-openai-deployment",
            "azure_openai_api_version_block_name": "azure-openai-api-version"
        }
    )
    print(f"Successfully created/updated deployment")

    # Instructions:
    # 1. Ensure the 'openai-api-key' Secret block exists in Prefect.
    #    prefect block create --name openai-api-key --value <your-openai-api-key>
    # 2. Ensure the 'thebh-dev' work pool exists.
    #    prefect work-pool create thebh-dev --type process
    # 3. Run this script to create the deployment:
    #    python deployment.py
    # 4. Start a worker for the pool:
    #    prefect worker start -p thebh-dev 