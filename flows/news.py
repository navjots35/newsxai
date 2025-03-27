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
@flow(name="ControlFlow News Extraction Pipeline v3")
def controlflow_news_pipeline(
    news_topic: str = "recent advancements in AI safety research", # Updated topic example
    openai_secret_block_name: str = "openai-api-key" # Name of your Prefect Secret block
):
    """
    Orchestrates the controlflow.ai news extraction pipeline using Prefect v3.
    """
    logger = get_run_logger()
    logger.info(f"Starting news extraction flow for topic: '{news_topic}'")

    # --- Load OpenAI API Key from Prefect Secret ---
    try:
        logger.info(f"Attempting to load secret block: {openai_secret_block_name}")
        openai_api_key_block = Secret.load(openai_secret_block_name)
        api_key_value = openai_api_key_block.get()
        logger.info(f"Successfully loaded secret block '{openai_secret_block_name}'.")

        # --- Configure ControlFlow ---
        # Option 1: Set Environment Variable (Recommended if supported)
        # Many libraries, potentially including controlflow, check this variable.
        os.environ["OPENAI_API_KEY"] = api_key_value
        logger.info("Set OPENAI_API_KEY environment variable for ControlFlow.")

        # Option 2: Attempt direct assignment (Original method - likely causing the error)
        # Keep this commented out unless you confirm 'openai_api_key' is the correct attribute
        # for your controlflow version via its documentation.
        # try:
        #     cf.settings.openai_api_key = api_key_value
        #     logger.info("Successfully set cf.settings.openai_api_key.")
        # except AttributeError as e:
        #     logger.error(f"Failed to set cf.settings.openai_api_key: {e}. "
        #                  f"This attribute may not exist or the method is incorrect. "
        #                  f"Relying on environment variable.")
        #     # If setting the environment variable is sufficient, we might not need to raise here.
        #     # If direct setting is mandatory and failed, uncomment the raise:
        #     # raise ValueError("Failed to configure ControlFlow API key via settings.") from e

        # Set default model (assuming this part is correct)
        cf.defaults.model = "openai/gpt-4o"
        logger.info(f"Set ControlFlow default model to '{cf.defaults.model}'.")

    except ObjectNotFound:
         # More specific exception handling in Prefect v3+
         logger.error(f"Prefect Secret block '{openai_secret_block_name}' not found. "
                      f"Please create it in the Prefect UI/API.")
         raise # Re-raise to fail the flow run clearly
    except Exception as e:
        # Catch other potential errors during secret loading or CF configuration
        logger.error(f"An unexpected error occurred loading the secret or configuring ControlFlow: {e}", exc_info=True)
        raise

    # --- Define ControlFlow Tasks (inside the Prefect flow) ---
    # These are controlflow.ai tasks, not Prefect tasks
    task_find_sources = cf.Task(
        objective=f"""
        Identify 2-3 recent and reputable news article URLs specifically about '{news_topic}'.
        Focus on major news outlets or respected tech/science publications.
        Return only a Python list of URL strings.
        Example format: ["url1", "url2", "url3"]
        """,
        result_type=list[str],
        name="CF - Find News Sources",
        model="openai/gpt-4o",
    )

    task_scrape_content = cf.Task(
        objective="""
        From the provided list of URLs, select the first URL.
        Use the 'fetch_url_content' tool to get the raw text content of that selected URL.
        Return only the raw text content obtained from the tool.
        If the tool returns an error message, return that error message.
        """,
        parents=[task_find_sources],
        tools=[fetch_url_content],
        result_type=str,
        name="CF - Scrape Article Content",
        model="openai/gpt-4o",
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
        parents=[task_scrape_content],
        result_type=dict,
        name="CF - Summarize and Organize News",
        model="openai/gpt-4o",
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
        parents=[task_organize_news],
        result_type=str,
        name="CF - Present News Report",
        model="openai/gpt-4o",
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
