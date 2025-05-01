# AI Personal Assistant with Chainlit

A web-based AI assistant that integrates with Azure OpenAI and various APIs to help with tasks like:
- Bank statement search and vector database querying
- Google Calendar management
- Google Tasks management
- Weather information via AccuWeather API
- Web searches via Google Custom Search API

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables in a `.env` file:
```
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
OPENAI_API_VERSION=your_api_version
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002

# Azure Cognitive Search Configuration
AZURE_SEARCH_ENDPOINT=your_search_service_name
AZURE_SEARCH_INDEX_NAME=bank-statements
AZURE_SEARCH_API_KEY=your_search_api_key
AZURE_SEARCH_API_VERSION=2023-11-01

# Google API Configuration
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_google_cse_id
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_PROJECT_ID=your_google_project_id
GOOGLE_REDIRECT_URI=http://localhost:8080

# AccuWeather API Configuration
ACCUWEATHER_API_KEY=your_accuweather_api_key
```

3. Run the Chainlit app:
```bash
chainlit run chainlit_app.py
```

4. Open your browser and navigate to http://localhost:8000

## Features

### Bank Statement Search
Search through your bank statements for transactions and financial information using Azure Cognitive Search with vector embeddings.

### Google Calendar
View and manage your calendar events and appointments using Google Calendar API.

### Google Tasks
Create, manage, and delete tasks and to-do lists using Google Tasks API.

Commands:
- Create new tasks: "Create a task to buy groceries"
- List all tasks: "Show me my tasks"
- Delete tasks: "Delete my task about buying groceries"

### Weather Information
Get current weather conditions and forecasts for any location using the AccuWeather API.

### Web Search
Search the web for general knowledge and current events using the Google Custom Search API.

## Usage Examples

- "What's the weather like in New York?"
- "Show me my calendar for tomorrow"
- "Create a new task to buy groceries"
- "Find transactions from Starbucks in my bank statements"
- "Search for information about Mars"
- "What do my bank statements show about spending on restaurants?"

## File Structure

- `chainlit_app.py` - Main application with Chainlit web interface
- `open-ai.py` - Azure OpenAI integration
- `vector.py` - Azure Cognitive Search vector database functions
- `weather.py` - AccuWeather API integration
- `search_api.py` - Google Search API integration
- `tasks.py` - Google Tasks API integration
- `calander.py` - Google Calendar API integration

## Authentication

For Google services (Calendar and Tasks), the application uses OAuth 2.0 authentication. The first time you use these services, you'll need to authorize the application by following the OAuth flow.

## Security Notes

All API keys and secrets are stored in environment variables for security. Never commit your `.env` file to version control. 