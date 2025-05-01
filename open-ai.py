import os
# Just import the main client class
from openai import AzureOpenAI
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType
from langchain_openai import AzureChatOpenAI
from langchain.tools import BaseTool
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage
from typing import Any, Optional

# Import functionality from your existing files
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

try:
    client = AzureOpenAI(
        azure_endpoint=azure_endpoint,
        api_key=azure_api_key,
        api_version=azure_api_version
    )
except Exception as e:
    print(f"Error initializing AzureOpenAI client: {e}")
    exit(1)

# --- Updated to use chat completions API instead of completions API ---
def get_openai_completion(prompt_text):
    """Gets a chat completion from Azure OpenAI using v1.x client."""
    if not client: # Check if client initialization failed
        print("AzureOpenAI client is not initialized.")
        return None
    try:
        # Use chat.completions.create instead of completions.create
        response = client.chat.completions.create(
            model=azure_deployment_name,
            messages=[
                {"role": "user", "content": prompt_text}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Azure OpenAI Error: {str(e)}")
        print("This could be due to authentication, invalid parameters, or other API issues.")
        print("Check your .env file values and Azure OpenAI configuration.")
        return None

# Example of how to call the function
if __name__ == "__main__":
    prompt = "Explain the difference between Google Calendar API and Google Tasks API."
    print(f"Sending prompt to Azure OpenAI (Deployment: {azure_deployment_name}):\n'{prompt}'")
    
    completion = get_openai_completion(prompt)
    
    if completion:
        print("\nAzure OpenAI Response:")
        print(completion)
    else:
        print("\nFailed to get response from Azure OpenAI.")

# Add the rest of your open-ai.py logic here...

# Initialize Azure OpenAI for LangChain
llm = AzureChatOpenAI(
    openai_api_version=os.getenv("OPENAI_API_VERSION"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    temperature=0
)

# Create custom tools using your existing code

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
        if "create" in query.lower() or "add" in query.lower():
            task_title = query.replace("create task", "").replace("add task", "").strip()
            result = tasks.create_task(task_title)
            if result:
                return f"Task '{task_title}' created successfully"
            else:
                return "Failed to create task"
        else:
            # Default to listing tasks
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

# Command-line interface for testing
if __name__ == "__main__":
    # Standard OpenAI completion functionality
    run_agent = input("Run LangChain agent? (y/n): ").strip().lower() == 'y'
    
    if run_agent:
        print("Welcome to your personal assistant! (Type 'exit' to quit)")
        print("I can help with:")
        print("- Bank statements")
        print("- Google Calendar")
        print("- Google Tasks")
        print("- Weather information")
        print("- Web searches")
        
        while True:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("Goodbye!")
                break
                
            try:
                response = agent.run(user_input)
                print(f"\nAssistant: {response}")
            except Exception as e:
                print(f"\nAssistant: Sorry, I encountered an error: {str(e)}")
    else:
        # Run standard OpenAI completion
        prompt = "Explain the difference between Google Calendar API and Google Tasks API."
        print(f"Sending prompt to Azure OpenAI (Deployment: {azure_deployment_name}):\n'{prompt}'")
        
        completion = get_openai_completion(prompt)
        
        if completion:
            print("\nAzure OpenAI Response:")
            print(completion)
        else:
            print("\nFailed to get response from Azure OpenAI.")