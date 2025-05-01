import os
import re
import chainlit as cl
from openai import AzureOpenAI
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from typing import Any, Optional

# Import functionality from existing files
from vector import search_client, embedding_model  # For vector search
import tasks  # Google Tasks functions
import calander  # Google Calendar functions
import weather  # Weather functions 
import search_api  # Web search functions

# Load environment variables from .env file
load_dotenv()

# Configure and initialize the Azure OpenAI client
azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
azure_api_version = os.getenv("OPENAI_API_VERSION")
azure_deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME") 

# --- Validation ---
if not all([azure_endpoint, azure_api_version, azure_api_key, azure_deployment_name]):
    print("Error: Missing one or more Azure OpenAI credentials in the .env file.")
    print("Ensure AZURE_OPENAI_ENDPOINT, OPENAI_API_VERSION, AZURE_OPENAI_API_KEY, and AZURE_OPENAI_DEPLOYMENT_NAME are set.")
    exit(1) 

# Initialize Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=azure_endpoint,
    api_key=azure_api_key,
    api_version=azure_api_version
)

# Initialize Azure OpenAI for LangChain
llm = AzureChatOpenAI(
    openai_api_version=os.getenv("OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0
)

# Create custom tools using existing code

# 1. Bank Statement Vector Search Tool
class BankStatementSearchTool(BaseTool):
    name: str = "bank_statement_search"
    description: str = "Search through bank statements for transactions or financial information. Use this when the user asks about their banking history, transactions, or financial records."
    
    def _run(self, query: str) -> str:
        try:
            # Generate embedding for the query
            vector = embedding_model.embed_query(query)
            
            # Search using vector - Fixed approach for Azure Cognitive Search
            results = search_client.search(
                search_text=query,
                vector_queries=[{
                    "kind": "vector",
                    "vector": vector,
                    "fields": "embedding",
                    "k": 3
                }],
                select=["text", "source", "page"]
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(f"Source: {result['source']}, Page: {result['page']}\n{result['text'][:500]}...")
            
            if not formatted_results:
                return "No relevant bank statement information found."
            
            return "Here's what I found in your bank statements:\n\n" + "\n\n".join(formatted_results)
        except Exception as e:
            return f"Error searching bank statements: {str(e)}"
    
    def _arun(self, query: str) -> Any:
        raise NotImplementedError("This tool does not support async")

# 2. Google Calendar Tool
class GoogleCalendarTool(BaseTool):
    name: str = "google_calendar"
    description: str = "Fetch events, check schedules, and manage calendar appointments. Use this for any questions about calendar events or scheduling."
    
    def _run(self, query: str) -> str:
        try:
            # Use our calendar.py functions
            events_list = calander.get_tomorrow_events()
            return "Calendar information:\n- " + "\n- ".join(events_list)
        except Exception as e:
            return f"Error accessing Google Calendar: {str(e)}"
    
    def _arun(self, query: str) -> Any:
        raise NotImplementedError("This tool does not support async")

# 3. Google Tasks Tool
class GoogleTasksTool(BaseTool):
    name: str = "google_tasks"
    description: str = "Manage tasks and to-do lists. Use this when users want to create tasks, view their to-do list, or manage tasks."
    
    def _run(self, query: str) -> str:
        # IMPORTANT: Check for deletion request first to avoid creating tasks with "delete" in title
        query_lower = query.lower()
        
        # Handle task deletion (check this first to prevent creating "delete" tasks)
        if any(word in query_lower for word in ["delete", "remove"]):
            # Get current tasks list first
            tasks_list = tasks.list_tasks()
            task_ids_to_delete = []
            
            # Case 1: Direct format "delete tasks: X and Y"
            if "delete tasks:" in query_lower:
                # Extract task titles
                task_content = query.split("delete tasks:", 1)[1].strip()
                
                # Remove any quotes from task content
                task_content = task_content.replace("'", "").replace('"', "")
                
                # Split by "and" if multiple tasks
                if " and " in task_content:
                    task_titles = [t.strip() for t in task_content.split(" and ")]
                else:
                    task_titles = [task_content.strip()]
                
                # Find IDs for each task title
                for title in task_titles:
                    task_id = tasks.extract_task_id_by_title(title)
                    if task_id:
                        task_ids_to_delete.append((title, task_id))
            
            # Case 2: Find any task ID in the request
            else:
                id_match = re.search(r'id[:\s]+([a-zA-Z0-9_-]+)', query, re.IGNORECASE)
                if id_match:
                    task_id = id_match.group(1)
                    task_ids_to_delete.append(("task with specified ID", task_id))
                else:
                    # Case 3: Try to match task titles in query
                    # Get a clean version of the query for matching
                    clean_query = query_lower
                    for word in ["delete", "remove", "task", "the", "my", "please", "can", "you", "about"]:
                        clean_query = clean_query.replace(word, " ").strip()
                    
                    # Get all tasks with IDs directly
                    all_tasks = tasks.get_tasks_with_ids()
                    
                    # Try to match task titles
                    for title, task_id in all_tasks:
                        # Try exact match
                        if clean_query and clean_query in title.lower():
                            task_ids_to_delete.append((title, task_id))
                            break
            
            # Delete all identified tasks
            if task_ids_to_delete:
                ids_only = [id_pair[1] for id_pair in task_ids_to_delete]
                success_count, failed_ids = tasks.delete_multiple_tasks(ids_only)
                
                if success_count == len(ids_only):
                    deleted_titles = ", ".join([f"'{pair[0]}'" for pair in task_ids_to_delete])
                    return f"Successfully deleted {success_count} task(s): {deleted_titles}"
                elif success_count > 0:
                    return f"Partially successful: Deleted {success_count} out of {len(ids_only)} task(s)."
                else:
                    return f"Failed to delete any tasks. Please try again."
            else:
                # If we couldn't identify any tasks to delete
                if tasks_list and tasks_list[0] != "No tasks found":
                    tasks_str = "\n- ".join(tasks_list)
                    return f"I couldn't identify which task to delete. Here are your current tasks:\n- {tasks_str}\n\nPlease specify which one to delete."
                else:
                    return "No tasks found to delete."
        
        # Handle task creation
        elif "create" in query_lower or "add" in query_lower:
            # Let the tasks.py module handle the cleaning of the task title
            result = tasks.create_task(query)
            if result:
                return f"Task '{result.get('title')}' created successfully"
            else:
                return "Failed to create task"
        
        # Default to listing tasks
        else:
            tasks_list = tasks.list_tasks()
            return "Your tasks:\n- " + "\n- ".join(tasks_list)
    
    def _arun(self, query: str) -> Any:
        raise NotImplementedError("This tool does not support async")

# 4. Weather Tool
class WeatherTool(BaseTool):
    name: str = "weather_info"
    description: str = "Get current weather and tomorrow's forecast for a location. Provides information about temperature, conditions, and chance of rain with recommendations for umbrella if rain is likely or drinking more water if hot. Use this when users ask about weather for today or tomorrow."
    
    def _run(self, query: str) -> str:
        # Improved location extraction logic
        # Remove common weather-related terms
        cleaned_query = query.lower().replace("weather", "").replace("forecast", "")
        cleaned_query = cleaned_query.replace("tomorrow", "").replace("today", "")
        cleaned_query = cleaned_query.replace("what's", "").replace("whats", "")
        cleaned_query = cleaned_query.replace("like", "").replace("in", "")
        cleaned_query = cleaned_query.replace("the", "").replace("for", "")
        # Remove the word "current" to avoid confusion with location names
        cleaned_query = cleaned_query.replace("current", "").strip()
        
        # If we have a location after cleaning, use it; otherwise use default
        location = cleaned_query if cleaned_query else "Houston"
        
        # If location looks like it might just be noise, use default
        if len(location) < 3:
            location = "Houston"
        
        return weather.get_weather(location)
    
    def _arun(self, query: str) -> Any:
        raise NotImplementedError("This tool does not support async")

# 5. Web Search Tool
class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for information. Use this for general knowledge questions or current events."
    
    def _run(self, query: str) -> str:
        return search_api.perform_google_search(query)
    
    def _arun(self, query: str) -> Any:
        raise NotImplementedError("This tool does not support async")

# Create tool instances
tools = [
    BankStatementSearchTool(),
    GoogleCalendarTool(),
    GoogleTasksTool(),
    WeatherTool(),
    WebSearchTool()
]

# Set up memory for conversation history
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Initialize the agent
agent = initialize_agent(
    tools,
    llm,
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
    verbose=True,
    memory=memory,
    handle_parsing_errors=True,
    system_message=SystemMessage(content="""
    You are a helpful assistant with access to various tools.
    For bank-related queries, use bank_statement_search.
    For calendar-related queries, use google_calendar.
    For task management, use google_tasks.
    For weather information, use weather_info.
    For general knowledge questions, use web_search.
    
    Always choose the most appropriate tool based on the user's question.
    Provide concise, accurate responses.
    """)
)

# Chainlit settings
@cl.on_chat_start
async def on_chat_start():
    """Initialize the chat session"""
    # Store agent in user session
    cl.user_session.set("agent", agent)
    
    # Welcome message
    await cl.Message(
        content="""Welcome to your personal assistant! I can help with:
- Bank statements and financial information
- Google Calendar events and scheduling
- Google Tasks and to-do lists
- Weather information for today and tomorrow
- Web searches for general knowledge

How can I help you today?"""
    ).send()

@cl.on_message
async def on_message(message: cl.Message):
    """Handle user message and generate response"""
    # Get agent from user session
    agent = cl.user_session.get("agent")
    
    # Create a new step for tracking agent's actions
    with cl.Step(name="Agent") as step:
        # Call the agent with user's message
        try:
            # Get response from agent
            response = await cl.make_async(agent.run)(message.content)
            
            # Send the response back to the user
            await cl.Message(content=response).send()
        except Exception as e:
            await cl.Message(
                content=f"Sorry, I encountered an error: {str(e)}"
            ).send()

# Add environment variable configuration for Chainlit
os.environ["OPENAI_API_TYPE"] = "azure"
os.environ["OPENAI_API_VERSION"] = azure_api_version
os.environ["OPENAI_API_BASE"] = azure_endpoint
os.environ["OPENAI_API_KEY"] = azure_api_key 