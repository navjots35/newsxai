# flows/controlflow_news.py

import os
import controlflow as cf
from controlflow.llm.messages import AIMessage
import requests
from bs4 import BeautifulSoup

# Prefect v3 imports (largely same as v2 for these core features)
from prefect import flow, task, get_run_logger
from prefect.blocks.system import Secret
from prefect.exceptions import ObjectNotFound

# --- Tool Definition (Keep as is) ---
@cf.tool
def fetch_url_content(url: str) -> str:
    """
    Fetches the main textual content from a given URL.
    Returns the extracted text or an error message.
    """
    logger = get_run_logger()
    logger.info(f"[Tool] Attempting to fetch content from: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # Increased timeout slightly
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()
        paragraphs = soup.find_all('p')
        text_content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
        if not text_content:
             # Fallback if no <p> tags found or they are empty
             text_content = soup.get_text(separator='\n', strip=True)
        logger.info(f"[Tool] Successfully fetched ~{len(text_content)} characters.")
        # Limit content length to avoid overwhelming the LLM context
        max_length = 8000
        return text_content[:max_length]
    except requests.exceptions.RequestException as e:
        logger.error(f"[Tool] Error fetching URL {url}: {e}")
        return f"Error: Could not fetch content from URL. {e}"
    except Exception as e:
        logger.error(f"[Tool] Error processing URL {url}: {e}")
        return f"Error: Could not process content from URL. {e}"

# --- Prefect Flow Definition ---
@flow(name="newsxai-extraction")
def controlflow_news_pipeline(
    news_topic: str = "recent advancements in AI safety research", # Updated topic example
    azure_openai_api_key_block_name: str = "azure-openai-api-key",
    azure_openai_endpoint_block_name: str = "azure-openai-endpoint",
    azure_openai_deployment_block_name: str = "azure-openai-deployment",
    azure_openai_api_version_block_name: str = "azure-openai-api-version"
):
    """
    Orchestrates the controlflow.ai news extraction pipeline using Prefect v3.
    """
    logger = get_run_logger()
    logger.info(f"Starting news extraction flow for topic: '{news_topic}'")

    # --- Load OpenAI API Key and Azure OpenAI credentials from Prefect Secrets ---
    try:
        logger.info(f"Attempting to load Azure OpenAI secret block: {azure_openai_api_key_block_name}")
        logger.info(f"Attempting to load Azure OpenAI secret block: {azure_openai_endpoint_block_name}")
        logger.info(f"Attempting to load Azure OpenAI secret block: {azure_openai_deployment_block_name}")
        logger.info(f"Attempting to load Azure OpenAI secret block: {azure_openai_api_version_block_name}")
        logger.info(f"Successfully loaded OpenAI secret block")
        
        # Load Azure OpenAI credentials from Prefect Secret blocks
        logger.info("Loading Azure OpenAI credential secrets from Prefect blocks")
        azure_api_key_block = Secret.load(azure_openai_api_key_block_name)
        azure_endpoint_block = Secret.load(azure_openai_endpoint_block_name)
        azure_deployment_block = Secret.load(azure_openai_deployment_block_name)
        azure_api_version_block = Secret.load(azure_openai_api_version_block_name)
        
        # Set environment variables using secret block values
        os.environ["AZURE_OPENAI_API_KEY"] = azure_api_key_block.get()
        os.environ["AZURE_OPENAI_ENDPOINT"] = azure_endpoint_block.get()
        os.environ["AZURE_OPENAI_DEPLOYMENT"] = azure_deployment_block.get()
        os.environ["AZURE_OPENAI_API_VERSION"] = azure_api_version_block.get()
        
        logger.info("Set Azure OpenAI environment variables from Prefect secrets")
        
        # Configure ControlFlow to use Azure OpenAI
        # Set API version first
        # cf.defaults.api_version = azure_api_version_block.get()
        # Then set the model using the correct format
        # cf.defaults.model = f"azure-openai/{azure_deployment_block.get()}"
        # logger.info(f"Set ControlFlow default API version to Azure OpenAI: '{cf.defaults.api_version}'")
        # logger.info(f"Set ControlFlow default model to Azure OpenAI: '{cf.defaults.model}'")
        
        # Alternative option using settings approach (as per documentation)
        cf.settings.llm_model = f"azure-openai/{azure_deployment_block.get()}"
        logger.info(f"Set ControlFlow settings model to Azure OpenAI: '{cf.settings.llm_model}'")
        
        # Alternative approach using direct model instantiation
        # from langchain_openai import AzureChatOpenAI
        # azure_model = AzureChatOpenAI(
        #     openai_api_version=azure_api_version_block.get(),
        #     azure_deployment=azure_deployment_block.get(),
        #     azure_endpoint=azure_endpoint_block.get(),
        #     api_key=azure_api_key_block.get()
        # )
        # cf.defaults.model = azure_model
        # logger.info("Set ControlFlow default model to Azure OpenAI using AzureChatOpenAI")

    except ObjectNotFound as e:
        # More specific exception to identify which secret block is missing
        logger.error(f"Prefect Secret block not found: {str(e)}")
        logger.error("Please create the following secret blocks in Prefect UI/API:")
        logger.error("  - azure-openai-api-key")
        logger.error("  - azure-openai-endpoint")
        logger.error("  - azure-openai-deployment")
        logger.error("  - azure-openai-api-version")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred loading secrets or configuring ControlFlow: {e}", exc_info=True)
        raise

    # --- Define ControlFlow Tasks (inside the Prefect flow) ---
    # These are controlflow.ai tasks, not Prefect tasks
    # Note: We don't need to specify model parameter for individual tasks
    # as they will use the default model configured above
    task_find_sources = cf.Task(
        objective=f"""
        Identify 2-3 recent and reputable news article URLs specifically about '{news_topic}'.
        Focus on major news outlets or respected tech/science publications.
        Return only a Python list of URL strings.
        Example format: ["url1", "url2", "url3"]
        """,
        result_type=list[str],
        name="CF - Find News Sources",
    )

    task_scrape_content = cf.Task(
        objective="""
        From the provided list of URLs, select the first URL.
        Use the 'fetch_url_content' tool to get the raw text content of that selected URL.
        Return only the raw text content obtained from the tool.
        If the tool returns an error message, return that error message.
        """,
        tools=[fetch_url_content],
        result_type=str,
        name="CF - Scrape Article Content",
    )

    task_organize_news = cf.Task(
        objective="""
        Analyze the provided raw news article text.
        If the text contains an error message starting with 'Error:',
        then return a dictionary like: {{"error": "Could not process article content."}}

        Otherwise, extract the main headline, provide a concise 2-3 sentence summary,
        and list 3-5 relevant keywords.
        Return this information as a single Python dictionary with keys:
        'headline' (string), 'summary' (string), and 'keywords' (list of strings).
        Example: {{"headline": "...", "summary": "...", "keywords": ["kw1", "kw2"]}}
        """,
        result_type=dict,
        name="CF - Summarize and Organize News",
    )

    task_present_news = cf.Task(
        objective="""
        Take the provided dictionary containing the organized news information
        (headline, summary, keywords) or an error message.
        Format this into a clean, human-readable report string.
        If there's an error key, report the error clearly.
        Otherwise, structure the report like this:

        --- News Report ---
        Headline: [The headline]
        Summary: [The summary]
        Keywords: [keyword1, keyword2, ...]
        -------------------
        """,
        result_type=str,
        name="CF - Present News Report",
    )

    # --- Run the ControlFlow Pipeline (inside the Prefect flow) ---
    logger.info("Running the controlflow.ai task sequence...")
    try:
        # Run the final controlflow.ai task; dependencies are handled by controlflow
        final_report_obj = task_present_news.run() # Returns AIMessage or result_type

        # Extract content for logging/returning
        if isinstance(final_report_obj, AIMessage):
            final_report = final_report_obj.content
        elif isinstance(final_report_obj, str):
            final_report = final_report_obj
        else:
            final_report = str(final_report_obj) # Fallback

        logger.info("Controlflow.ai sequence finished.")
        logger.info(f"Final Report:\n{final_report}")

        # Return the final report from the Prefect flow
        return final_report

    except Exception as e:
        logger.error(f"An error occurred during the controlflow.ai execution: {e}", exc_info=True)
        # Re-raise the exception to mark the Prefect flow run as failed
        raise

# Note: No `if __name__ == "__main__":` block needed here
