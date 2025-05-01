import os
from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re

# Load environment variables from .env file
load_dotenv()

SCOPES_TASKS = ['https://www.googleapis.com/auth/tasks']

# Common prefixes to clean from task creation requests
TASK_CREATION_PREFIXES = [
    "create a new task to",
    "create new task to",
    "create a task to",
    "create task to",
    "add a new task to",
    "add new task to",
    "add a task to",
    "add task to",
    "create a new task",
    "create new task",
    "create a task",
    "create task",
    "add a new task",
    "add new task",
    "add a task",
    "add task"
]

def clean_task_title(title):
    """Clean a task title by removing common prefixes.
    
    Args:
        title (str): The raw task title from user input
        
    Returns:
        str: Cleaned task title
    """
    title = title.strip()
    
    # Remove common prefixes
    lower_title = title.lower()
    for prefix in TASK_CREATION_PREFIXES:
        if lower_title.startswith(prefix):
            title = title[len(prefix):].strip()
            break
    
    # Remove any leading colon and whitespace
    title = title.lstrip(': ')
    
    return title

def authenticate_google_tasks():
    # Construct the client configuration from environment variables
    client_config = {
        "installed": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "project_id": os.getenv("GOOGLE_PROJECT_ID"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI")]
        }
    }

    # Validate that necessary variables were loaded
    if not all([client_config["installed"]["client_id"], client_config["installed"]["client_secret"], client_config["installed"]["project_id"], client_config["installed"]["redirect_uris"][0]]):
        print("Error: Missing one or more Google credentials in the .env file (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_PROJECT_ID, GOOGLE_REDIRECT_URI).")
        return None

    try:
        # Use from_client_config instead of from_client_secrets_file
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES_TASKS)
        # Using port=0 lets the OS pick an available port automatically
        creds = flow.run_local_server(port=0)
        return creds
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        # Update error handling similarly to calander.py
        if "Only one usage of each socket" in str(e):
            print("\nPort conflict detected. Another application is using the specified port.")
        elif "invalid_grant" in str(e) or "invalid_client" in str(e):
             print("\nError: Invalid grant/client. This might mean your credentials (client ID/secret) in .env are wrong, or the refresh token is expired/revoked.")
        elif "redirect_uri_mismatch" in str(e):
             print(f"\nError: Redirect URI mismatch. Ensure the URI in your .env ('{os.getenv('GOOGLE_REDIRECT_URI')}') is registered in Google Cloud Console for your client ID.")
        return None

def create_task(title):
    """Create a new task with the given title.
    
    Args:
        title (str): The title of the task to create
        
    Returns:
        dict: The created task object or None if creation failed
    """
    # Clean the task title first
    cleaned_title = clean_task_title(title)
    
    creds = authenticate_google_tasks()
    if creds is None:
        print("Failed to authenticate with Google Tasks. Cannot create task.")
        return None
        
    try:
        service = build('tasks', 'v1', credentials=creds)
        task = {'title': cleaned_title}
        result = service.tasks().insert(tasklist='@default', body=task).execute()
        print(f"Task '{result.get('title', cleaned_title)}' created successfully (ID: {result.get('id')})")
        return result
    except Exception as e:
        print(f"Error creating task: {str(e)}")
        return None

def list_tasks():
    creds = authenticate_google_tasks()
    if creds is None:
        print("Failed to authenticate with Google Tasks. Cannot list tasks.")
        return ["Authentication failed. Check previous error messages."]
        
    try:
        service = build('tasks', 'v1', credentials=creds)
        # Request specific fields to potentially make it slightly faster if needed
        # fields='items(id,title,status)'
        tasks_result = service.tasks().list(tasklist='@default').execute() 
        tasks = tasks_result.get('items', [])
        if not tasks:
            return ["No tasks found"]
        # Return more info potentially, e.g., task status or ID
        return [f"{task.get('title', 'Untitled')} (ID: {task.get('id')})" for task in tasks] 
    except Exception as e:
        print(f"Error listing tasks: {str(e)}")
        return [f"Error listing tasks. Check logs for details."]

def delete_task(task_id):
    """Delete a task by its ID from Google Tasks.
    
    Args:
        task_id (str): The ID of the task to delete
        
    Returns:
        bool: True if the task was successfully deleted, False otherwise
    """
    creds = authenticate_google_tasks()
    if creds is None:
        print("Failed to authenticate with Google Tasks. Cannot delete task.")
        return False
        
    try:
        service = build('tasks', 'v1', credentials=creds)
        # Execute delete operation
        service.tasks().delete(tasklist='@default', task=task_id).execute()
        print(f"Task with ID '{task_id}' deleted successfully")
        return True
    except Exception as e:
        print(f"Error deleting task: {str(e)}")
        if "404" in str(e):
            print(f"Task with ID '{task_id}' not found")
        return False

def delete_multiple_tasks(task_ids):
    """Delete multiple tasks by their IDs.
    
    Args:
        task_ids (list): List of task IDs to delete
        
    Returns:
        tuple: (int, list) - Count of successfully deleted tasks and list of failed task IDs
    """
    creds = authenticate_google_tasks()
    if creds is None:
        print("Failed to authenticate with Google Tasks. Cannot delete tasks.")
        return 0, task_ids
    
    success_count = 0
    failed_ids = []
    
    try:
        service = build('tasks', 'v1', credentials=creds)
        
        for task_id in task_ids:
            try:
                service.tasks().delete(tasklist='@default', task=task_id).execute()
                success_count += 1
                print(f"Task with ID '{task_id}' deleted successfully")
            except Exception as e:
                print(f"Error deleting task with ID '{task_id}': {str(e)}")
                failed_ids.append(task_id)
        
        return success_count, failed_ids
    except Exception as e:
        print(f"Error during batch deletion: {str(e)}")
        return success_count, failed_ids

def get_tasks_with_ids():
    """Get list of tasks with their IDs.
    
    Returns:
        list: List of tuples (task_title, task_id)
    """
    creds = authenticate_google_tasks()
    if creds is None:
        print("Failed to authenticate with Google Tasks. Cannot list tasks.")
        return []
        
    try:
        service = build('tasks', 'v1', credentials=creds)
        tasks_result = service.tasks().list(tasklist='@default').execute() 
        tasks = tasks_result.get('items', [])
        
        if not tasks:
            return []
        
        return [(task.get('title', 'Untitled'), task.get('id')) for task in tasks]
    except Exception as e:
        print(f"Error listing tasks with IDs: {str(e)}")
        return []

def extract_task_id(task_string):
    """Extract task ID from a task string in the format 'Title (ID: task_id)'
    
    Args:
        task_string (str): The task string containing the ID
        
    Returns:
        str: The extracted task ID or None if not found
    """
    try:
        # Extract text between "(ID: " and ")"
        match = re.search(r'\(ID: (.*?)\)', task_string)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"Error extracting task ID: {str(e)}")
        return None

def extract_task_id_by_title(title):
    """Find a task ID by matching the task title.
    
    Args:
        title (str): The title of the task to find
        
    Returns:
        str: The task ID if found, None otherwise
    """
    tasks_with_ids = get_tasks_with_ids()
    
    # Try exact match first
    for task_title, task_id in tasks_with_ids:
        if task_title.lower() == title.lower():
            return task_id
    
    # Try partial match if exact match fails
    for task_title, task_id in tasks_with_ids:
        if title.lower() in task_title.lower():
            return task_id
    
    return None

# Usage example:
if __name__ == "__main__":
    print("\nCreating a new task...")
    created_task = create_task("Prepare hackathon demo v2")
    if created_task:
        print("\nCurrent tasks:")
        tasks_list = list_tasks()
        for task_str in tasks_list:
            print(f"- {task_str}")
        
        # Example of deleting a task (uncomment to test)
        # if tasks_list and tasks_list[0] != "No tasks found":
        #     task_id = extract_task_id(tasks_list[0])
        #     if task_id:
        #         print(f"\nDeleting task with ID: {task_id}")
        #         if delete_task(task_id):
        #             print("Task deleted successfully.")
        #             print("\nUpdated tasks:")
        #             updated_tasks = list_tasks()
        #             for task_str in updated_tasks:
        #                 print(f"- {task_str}")
        #         else:
        #             print("Failed to delete task.")
    else:
        print("Task creation failed.")
