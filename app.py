import streamlit as st
import pickle
import os
import json
import base64
from datetime import datetime, date
import pandas as pd
from dotenv import load_dotenv
from io import BytesIO
import drive_utils

# --- Must be the first Streamlit command ---
st.set_page_config(layout="wide")

# --- Load environment variables and global configs ---
load_dotenv()
# Use an absolute path with os.path.join for better path handling
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(DATA_DIR, 'project_data_v2.pkl')
APP_PASSWORD = os.environ.get("PROJECT_APP_PASSWORD")

# --- Data Persistence and State Initialization Functions ---
def initialize_state():
    """Initialize session state variables if they don't exist or need defaults."""
    if 'projects' not in st.session_state:
        st.session_state.projects = {}
        print("DEBUG: Initialized empty projects in session state.")
    if 'next_project_id_num' not in st.session_state:
        st.session_state.next_project_id_num = 1
        print("DEBUG: Initialized next_project_id_num to 1.")
    if 'tasks_expanded' not in st.session_state:
        st.session_state.tasks_expanded = {}
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    # Ensure app_initialized flag exists
    if 'app_initialized' not in st.session_state:
        st.session_state.app_initialized = False
    # Add flag to track if data needs saving
    if 'data_changed' not in st.session_state:
        st.session_state.data_changed = False


def save_data():
    """Save project data to a pickle file."""
    print(f"DEBUG: Attempting to save data to {DATA_FILE}...")
    # print(f"DEBUG: Data to be saved: {st.session_state.projects}") # Can be very verbose
    data_to_save = {
        'projects': st.session_state.projects,
        'next_project_id_num': st.session_state.next_project_id_num
    }
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    
    try:
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(data_to_save, f)
        print(f"DEBUG: Data successfully saved to {DATA_FILE}")
        st.toast(f"Data saved successfully!", icon="💾")
        # Reset the data_changed flag after saving
        st.session_state.data_changed = False
        return True
    except Exception as e:
        print(f"DEBUG: ERROR SAVING DATA: {e}")
        st.error(f"Failed to save data: {e}")
        return False

def load_data():
    """Load project data from pickle file if it exists, then initialize state."""
    print(f"DEBUG: Attempting to load data from {DATA_FILE}...")
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                loaded_data = pickle.load(f)
                st.session_state.projects = loaded_data.get('projects', {})
                st.session_state.next_project_id_num = loaded_data.get('next_project_id_num', 1)
                print(f"DEBUG: Data successfully loaded from {DATA_FILE}.")
                print(f"DEBUG: Loaded {len(st.session_state.projects)} projects.")
                print(f"DEBUG: Next project ID: {st.session_state.next_project_id_num}")
                
                # Ensure all projects and tasks have a notes field
                for project_id, project_data in st.session_state.projects.items():
                    if 'notes' not in project_data:
                        project_data['notes'] = ""
                    for task in project_data['tasks']:
                        if 'notes' not in task:
                            task['notes'] = ""
                
                if st.session_state.projects:
                    st.toast("Your project data has been loaded successfully!", icon="📊")
                
                return True
        except Exception as e:
            print(f"DEBUG: ERROR LOADING DATA from {DATA_FILE}: {e}. Initializing fresh state.")
            st.error(f"Error loading data file: {e}. Starting with a fresh state.")
            st.session_state.projects = {} # Ensure clean state on error
            st.session_state.next_project_id_num = 1
            return False
    else:
        print(f"DEBUG: Data file {DATA_FILE} not found. Initializing fresh state.")
        return False

# Function to mark data as changed and trigger auto-save
def mark_data_changed():
    """Mark data as changed to trigger auto-save."""
    st.session_state.data_changed = True

# Auto-save hook that runs on every rerun if data has changed
def auto_save_if_needed():
    """Automatically save data if it has been changed."""
    if st.session_state.get('data_changed', False) and st.session_state.get('logged_in', False):
        print("DEBUG: Auto-saving data because changes were detected...")
        save_data()

# --- Initial Data Load and State Setup (runs once per session) ---
if not st.session_state.get('app_initialized', False):
    initialize_state()
    success = load_data()
    if not success:
        print("DEBUG: Initial data load failed or no data file exists.")
    st.session_state.app_initialized = True
else:
    # On subsequent reruns, ensure core state keys exist
    initialize_state()
    # Try to auto-save if data has changed
    auto_save_if_needed()


# --- Password Protection and Login UI ---
def display_login_form():
    """Displays the login form and handles login logic."""
    st.title("Login Required")
    if APP_PASSWORD is None:
        st.error("CRITICAL: Application password not configured.")
        st.info("Please set the 'PROJECT_APP_PASSWORD' environment variable (e.g., in your .env file if running locally).")
        return # Stop further login UI if password isn't even set

    st.write("Please enter the password to access the Project Manager.")
    password_attempt = st.text_input("Password", type="password", key="password_input_main_app") # Unique key
    if st.button("Login", key="login_button_main_app"): # Unique key
        if password_attempt == APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun() # Use st.rerun() instead of deprecated experimental_rerun
        else:
            st.error("Incorrect password. Please try again.")

# --- Main Application Logic ---
def run_main_app():
    """Runs the main part of the Streamlit application after successful login."""
    st.title("Personal Project Manager")
    st.markdown("Manage your personal projects and tasks effectively.")

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Projects Dashboard", "Add/Edit Project", "Manage Tasks", "Google Drive Integration"],
        key="navigation_page_main_app" # Unique key
    )
    st.sidebar.markdown("---")
    
    # Display data file location and status
    st.sidebar.markdown(f"**Data file location:**")
    st.sidebar.code(DATA_FILE, language=None)
    if os.path.exists(DATA_FILE):
        file_size = os.path.getsize(DATA_FILE)
        file_time = datetime.fromtimestamp(os.path.getmtime(DATA_FILE))
        st.sidebar.markdown(f"**Last saved:** {file_time.strftime('%Y-%m-%d %H:%M:%S')}")
        st.sidebar.markdown(f"**File size:** {file_size} bytes")
    else:
        st.sidebar.warning("No data file exists yet")
    
    # Manual save button (still useful despite auto-save)
    if st.sidebar.button("Save All Data Now"):
        save_data()
        
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.tasks_expanded = {} # Clear task expansion state on logout
        # Save data before logging out
        if st.session_state.data_changed:
            save_data()
        st.rerun() # Use st.rerun() instead of deprecated experimental_rerun

    # Helper function for project display
    def get_project_display_name(project_id):
        if project_id in st.session_state.projects:
            return f"{project_id}: {st.session_state.projects[project_id]['name']}"
        return project_id

    # --- Page: Projects Dashboard ---
    if page == "Projects Dashboard":
        st.header("Projects Dashboard")
        # (Code for Projects Dashboard - unchanged from your latest, but ensure variable names are consistent)
        if not st.session_state.projects:
            st.info("No projects yet. Go to 'Add/Edit Project' to create one!")
        else:
            project_data_list = [] # Renamed from project_data to avoid confusion if df also named project_data
            for project_id, project_details in st.session_state.projects.items():
                total_tasks = len(project_details['tasks'])
                completed_tasks = sum(1 for task in project_details['tasks'] if task['status'] == 'Completed')
                progress = 0 if total_tasks == 0 else round((completed_tasks / total_tasks) * 100)
                project_data_list.append({
                    'ID': project_id, 'Name': project_details['name'],
                    'Description': project_details['description'][:50] + '...' if len(project_details['description']) > 50 else project_details['description'],
                    'Created': project_details['created_date'], 'Tasks': total_tasks, 'Progress': f"{progress}%"
                })
            if project_data_list:
                df = pd.DataFrame(project_data_list)
                st.dataframe(df, use_container_width=True)
                st.subheader("Project Details & Tasks")
                project_ids = list(st.session_state.projects.keys())
                selected_project_id_dashboard = st.selectbox(
                    "Select a project to view details", options=project_ids,
                    format_func=get_project_display_name, key="dashboard_project_select_main_app" # Unique key
                )
                if selected_project_id_dashboard and selected_project_id_dashboard in st.session_state.projects:
                    project_details_selected = st.session_state.projects[selected_project_id_dashboard]
                    st.markdown(f"### {project_details_selected['name']} (`{selected_project_id_dashboard}`)")
                    st.markdown(f"**Description:** {project_details_selected['description']}")
                    st.markdown(f"**Created:** {project_details_selected['created_date']}")
                    
                    # Display project notes
                    st.markdown("#### Project Notes")
                    if project_details_selected.get('notes'):
                        st.info(project_details_selected.get('notes'))
                    else:
                        st.info("No notes for this project yet. Go to 'Add/Edit Project' to add notes.")
                    
                    st.markdown("#### Tasks")
                    if not project_details_selected['tasks']:
                        st.info("No tasks for this project yet. Go to 'Manage Tasks' to add some.")
                    else:
                        # Add a filter for showing task notes
                        show_notes = st.checkbox("Show task notes", key=f"show_notes_{selected_project_id_dashboard}")
                        
                        if show_notes:
                            # Display tasks with notes in an expandable format
                            for i, task in enumerate(project_details_selected['tasks']):
                                with st.expander(f"{i+1}. {task['name']} - Due: {task['due_date'] or 'N/A'} - Status: {task['status']}"):
                                    if task.get('notes'):
                                        st.info(task.get('notes'))
                                    else:
                                        st.info("No notes for this task.")
                        else:
                            # Traditional task table view without notes
                            task_list_data = [{'#': i + 1, 'Task': task['name'], 'Due Date': task['due_date'], 'Status': task['status']}
                                            for i, task in enumerate(project_details_selected['tasks'])]
                            st.table(pd.DataFrame(task_list_data).set_index('#'))
            else:
                st.info("No projects available to display.")


    # --- Page: Add/Edit Project ---
    elif page == "Add/Edit Project":
        st.header("Add or Edit Project")
        # (Code for Add/Edit Project - unchanged from your latest, but ensure variable names and keys)
        action = st.radio("Select Action", ["Create New Project", "Edit Existing Project", "Delete Project"],
                          key="project_action_radio_main_app", horizontal=True) # Unique key
        if action == "Create New Project":
            st.subheader("Create New Project")
            with st.form("new_project_form_main_app", clear_on_submit=True): # Unique key
                project_name = st.text_input("Project Name", key="new_proj_name_main_app")
                project_description = st.text_area("Project Description", key="new_proj_desc_main_app")
                project_notes = st.text_area("Project Notes (Optional)", key="new_proj_notes_main_app", 
                                          placeholder="Add any notes, comments, or additional context for this project...")
                submitted = st.form_submit_button("Create Project")
                if submitted:
                    if not project_name: st.error("Project name is required!")
                    else:
                        project_id = f"P{st.session_state.next_project_id_num}"
                        st.session_state.next_project_id_num += 1
                        st.session_state.projects[project_id] = {
                            'name': project_name, 
                            'description': project_description,
                            'created_date': datetime.now().strftime("%Y-%m-%d"), 
                            'tasks': [],
                            'notes': project_notes  # Add notes field
                        }
                        # Mark data as changed to trigger auto-save
                        mark_data_changed()
                        # Also save immediately
                        save_data()
                        st.success(f"Project '{project_name}' created successfully with ID: {project_id}")
                        st.balloons()
        elif action == "Edit Existing Project":
            st.subheader("Edit Existing Project")
            if not st.session_state.projects: st.info("No projects to edit. Create one first.")
            else:
                project_ids = list(st.session_state.projects.keys())
                project_to_edit_id = st.selectbox("Select Project to Edit", options=project_ids,
                                                  format_func=get_project_display_name, key="edit_project_select_main_app")
                if project_to_edit_id:
                    project_data_val = st.session_state.projects[project_to_edit_id]
                    with st.form(f"edit_project_form_{project_to_edit_id}_main_app"): # Unique key
                        st.markdown(f"Editing Project ID: **{project_to_edit_id}**")
                        edit_project_name = st.text_input("Project Name", value=project_data_val['name'],
                                                          key=f"edit_proj_name_{project_to_edit_id}_main_app")
                        edit_project_description = st.text_area("Project Description", value=project_data_val['description'],
                                                                key=f"edit_proj_desc_{project_to_edit_id}_main_app")
                        # Add notes field with existing notes
                        edit_project_notes = st.text_area("Project Notes", 
                                                        value=project_data_val.get('notes', ''),
                                                        key=f"edit_proj_notes_{project_to_edit_id}_main_app",
                                                        placeholder="Add any notes, comments, or additional context for this project...")
                        edit_submitted = st.form_submit_button("Update Project")
                        if edit_submitted:
                            if not edit_project_name: st.error("Project name cannot be empty!")
                            else:
                                st.session_state.projects[project_to_edit_id]['name'] = edit_project_name
                                st.session_state.projects[project_to_edit_id]['description'] = edit_project_description
                                st.session_state.projects[project_to_edit_id]['notes'] = edit_project_notes
                                # Mark data as changed to trigger auto-save
                                mark_data_changed()
                                # Also save immediately
                                save_data()
                                st.success(f"Project '{edit_project_name}' updated successfully!")
                                st.rerun()
        elif action == "Delete Project":
            st.subheader("Delete Project")
            if not st.session_state.projects: st.info("No projects to delete.")
            else:
                project_ids = list(st.session_state.projects.keys())
                project_to_delete_id = st.selectbox("Select Project to Delete", options=project_ids,
                                                    format_func=get_project_display_name, key="delete_project_select_main_app")
                if project_to_delete_id:
                    project_name_to_delete = st.session_state.projects[project_to_delete_id]['name']
                    st.warning(f"Are you sure you want to delete project '{project_name_to_delete}' ({project_to_delete_id})? This will delete all tasks.")
                    if st.button(f"Yes, Delete Project '{project_name_to_delete}'", key=f"confirm_delete_btn_{project_to_delete_id}_main_app"):
                        del st.session_state.projects[project_to_delete_id]
                        keys_to_del = [k for k in st.session_state.tasks_expanded if k.startswith(project_to_delete_id)]
                        for k_del in keys_to_del: del st.session_state.tasks_expanded[k_del]
                        # Mark data as changed to trigger auto-save
                        mark_data_changed()
                        # Also save immediately
                        save_data()
                        st.success(f"Project '{project_name_to_delete}' deleted successfully.")
                        st.rerun()

    # --- Page: Manage Tasks ---
    elif page == "Manage Tasks":
        st.header("Manage Tasks")
        # (Code for Manage Tasks - unchanged from your latest, but ensure variable names and keys)
        if not st.session_state.projects: st.info("No projects yet. Create a project first.")
        else:
            project_ids = list(st.session_state.projects.keys())
            selected_project_id_tasks = st.selectbox("Select Project", options=project_ids,
                                                     format_func=get_project_display_name, key="manage_tasks_project_select_main_app")
            if selected_project_id_tasks:
                project_val = st.session_state.projects[selected_project_id_tasks]
                st.subheader(f"Tasks for: {project_val['name']} (`{selected_project_id_tasks}`)")
                
                # Show project notes at the top of the tasks page
                if project_val.get('notes'):
                    with st.expander("View Project Notes", expanded=False):
                        st.info(project_val.get('notes'))
                        if st.button("Edit Project Notes", key=f"edit_project_notes_btn_{selected_project_id_tasks}"):
                            # Switch to Edit Project page
                            st.session_state['navigation_page_main_app'] = 1  # Index for "Add/Edit Project"
                            st.rerun()
                
                if project_val['tasks']:
                    for i, task in enumerate(project_val['tasks']):
                        task_key_prefix = f"task_{selected_project_id_tasks}_{i}_main_app"
                        task_edit_state_key = f"{selected_project_id_tasks}_{i}"
                        cols = st.columns([3, 2, 2, 0.8, 0.8, 0.8])
                        is_editing = st.session_state.tasks_expanded.get(task_edit_state_key, False)

                        with cols[0]:
                            if is_editing: new_name = st.text_input("Name", value=task['name'], key=f"{task_key_prefix}_name_edit", label_visibility="collapsed")
                            else: st.markdown(f"**{i+1}. {task['name']}**")
                        with cols[1]:
                            if is_editing:
                                current_due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date() if task['due_date'] else date.today()
                                new_due_date = st.date_input("Due", value=current_due_date, key=f"{task_key_prefix}_due_edit", label_visibility="collapsed")
                            else: st.markdown(task['due_date'] or "N/A")
                        with cols[2]:
                            if is_editing:
                                status_options = ["Not Started", "In Progress", "Completed", "Blocked"]
                                current_status_idx = status_options.index(task['status']) if task['status'] in status_options else 0
                                new_status = st.selectbox("Status", options=status_options, index=current_status_idx,
                                                          key=f"{task_key_prefix}_status_edit", label_visibility="collapsed")
                            else: st.markdown(task['status'])
                        with cols[3]:
                            if st.button("✏️" if not is_editing else "🔽", key=f"{task_key_prefix}_toggle_edit", help="Edit Task" if not is_editing else "Collapse Edit"):
                                st.session_state.tasks_expanded[task_edit_state_key] = not is_editing
                                st.rerun()
                        if is_editing:
                            with cols[4]:
                                if st.button("💾", key=f"{task_key_prefix}_update", help="Save Task Changes"):
                                    if not new_name.strip(): st.error("Task name cannot be empty.")
                                    else:
                                        project_val['tasks'][i]['name'] = new_name
                                        project_val['tasks'][i]['due_date'] = new_due_date.strftime("%Y-%m-%d") if new_due_date else None
                                        project_val['tasks'][i]['status'] = new_status
                                        st.session_state.tasks_expanded[task_edit_state_key] = False
                                        # Mark data as changed to trigger auto-save
                                        mark_data_changed()
                                        # Also save immediately
                                        save_data()
                                        st.success(f"Task '{new_name}' updated!")
                                        st.rerun()
                        else:
                            with cols[4]: st.empty()
                        with cols[5]:
                            if st.button("🗑️", key=f"{task_key_prefix}_delete", help="Delete Task"):
                                deleted_task_name = project_val['tasks'].pop(i)['name']
                                if task_edit_state_key in st.session_state.tasks_expanded:
                                    del st.session_state.tasks_expanded[task_edit_state_key]
                                # Mark data as changed to trigger auto-save
                                mark_data_changed()
                                # Also save immediately
                                save_data()
                                st.success(f"Task '{deleted_task_name}' deleted.")
                                st.rerun()
                        
                        # Display task notes if they exist or if in edit mode
                        if is_editing:
                            new_notes = st.text_area("Task Notes", value=task.get('notes', ''), 
                                                  key=f"{task_key_prefix}_notes_edit",
                                                  placeholder="Add any notes, comments, or details for this task...")
                            project_val['tasks'][i]['notes'] = new_notes
                            mark_data_changed()
                        elif task.get('notes'):
                            with st.expander("Task Notes", expanded=False):
                                st.info(task.get('notes'))
                        
                        st.divider()
                else: st.info("No tasks for this project yet.")

                st.subheader("Add New Task")
                with st.form(f"add_task_form_{selected_project_id_tasks}_main_app", clear_on_submit=True): # Unique key
                    task_name = st.text_input("Task Name", key=f"new_task_name_{selected_project_id_tasks}_main_app")
                    task_due_date = st.date_input("Due Date", value=date.today(), key=f"new_task_due_{selected_project_id_tasks}_main_app")
                    task_status = st.selectbox("Status", ["Not Started", "In Progress", "Completed", "Blocked"],
                                               key=f"new_task_status_{selected_project_id_tasks}_main_app")
                    # Add task notes field
                    task_notes = st.text_area("Task Notes (Optional)", key=f"new_task_notes_{selected_project_id_tasks}_main_app",
                                           placeholder="Add any notes, comments, or details for this task...")
                    add_task_submitted = st.form_submit_button("Add Task")
                    if add_task_submitted:
                        if not task_name: st.error("Task name is required!")
                        else:
                            project_val['tasks'].append({
                                'name': task_name, 
                                'due_date': task_due_date.strftime("%Y-%m-%d") if task_due_date else None,
                                'status': task_status,
                                'notes': task_notes  # Add notes field
                            })
                            # Mark data as changed to trigger auto-save
                            mark_data_changed()
                            # Also save immediately
                            save_data()
                            st.success(f"Task '{task_name}' added to '{project_val['name']}'!")
                            

    elif page == "Google Drive Integration":
        st.header("Google Drive Integration")

        # Initialize Drive service
        # Ensure drive_utils is imported
        drive_service = drive_utils.get_drive_service()

        if drive_service:
            st.success("Connected to Google Drive")

            # Create tabs for different operations
            tab1, tab2, tab3 = st.tabs(["Save to Drive", "Load from Drive", "Settings"])

            with tab1:
                st.subheader("Save Projects to Google Drive")
                folder_name = st.text_input("Folder Name", value="ProjectManager")

                if st.button("Save to Drive"):
                    with st.spinner("Saving to Drive..."):
                        # Get or create folder
                        folder_id = drive_utils.get_or_create_folder(drive_service, folder_name)

                        if folder_id:
                            # Prepare data to save
                            # Ensure session_state keys 'projects' and 'next_project_id_num' exist
                            data_to_save = {
                                'projects': st.session_state.get('projects', {}), # Use .get for safety
                                'next_project_id_num': st.session_state.get('next_project_id_num', 1) # Use .get for safety
                            }

                            # Generate filename with timestamp
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            file_name = f"project_data_{timestamp}.pkl"

                            # Save to Drive
                            file_id = drive_utils.save_projects_to_drive(
                                drive_service, data_to_save, file_name, folder_id
                            )

                            if file_id:
                                st.success(f"Projects saved to Drive in folder '{folder_name}'")
                                st.balloons()

            with tab2:
                st.subheader("Load Projects from Google Drive")

                # List pickle files in Drive
                pkl_files = drive_utils.list_files(
                    drive_service,
                    query="mimeType='application/octet-stream' and name contains '.pkl'"
                )

                if not pkl_files:
                    st.info("No project files found in Google Drive.")
                else:
                    # Format file options
                    file_options = {f"{file['name']} (Modified: {file['modifiedTime']})": file['id']
                                  for file in pkl_files}

                    selected_file = st.selectbox(
                        "Select a file to load",
                        options=list(file_options.keys())
                    )

                    if selected_file and st.button("Load Selected File"):
                        with st.spinner("Loading from Drive..."):
                            file_id = file_options[selected_file]
                            data = drive_utils.load_projects_from_drive(drive_service, file_id)

                            if data and 'projects' in data and 'next_project_id_num' in data:
                                # Confirm before replacing
                                st.warning("This will replace your current projects data. Continue?")
                                if st.button("Confirm Load"):
                                    st.session_state.projects = data['projects']
                                    st.session_state.next_project_id_num = data['next_project_id_num']
                                    # IMPORTANT: Ensure mark_data_changed() and save_data() are defined/imported in app.py
                                    # If not, this will cause an error. Let's assume they are for now.
                                    try:
                                        mark_data_changed()
                                        save_data()
                                        st.success("Projects loaded from Drive successfully!")
                                        st.balloons()
                                    except NameError as e:
                                        st.error(f"Error: Required function not found: {e}. Please ensure 'mark_data_changed' and 'save_data' are defined in app.py.")


            with tab3:
                st.subheader("Google Drive Settings")
                st.info("""
                To use Google Drive integration, you need to:
                1. Create a Google Cloud project
                2. Enable the Google Drive API
                3. Create service account credentials
                4. Download the credentials as JSON
                5. Either upload the credentials file below or set it in your Streamlit secrets
                """)

                uploaded_creds = st.file_uploader("Upload credentials.json", type="json")
                if uploaded_creds:
                    # Ensure drive_utils.CREDENTIALS_FILE is defined
                    creds_path = getattr(drive_utils, 'CREDENTIALS_FILE', 'credentials.json') # Default if not found
                    try:
                        with open(creds_path, "wb") as f:
                            f.write(uploaded_creds.getbuffer())
                        st.success(f"Credentials saved to {creds_path}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save credentials: {e}")
        else:
            st.error("Not connected to Google Drive")
            st.info("Please upload your Google Drive API credentials in the Settings tab or configure Streamlit secrets.")

    # --- Page: Data Backup/Restore ---
    elif page == "Data Backup/Restore":
        st.header("Data Backup & Restore")
        
        # Function to create a download link for a JSON file
        def get_download_link(data, filename):
            # Convert data to JSON string
            json_str = json.dumps(data, indent=4)
            # Encode to base64
            b64 = base64.b64encode(json_str.encode()).decode()
            href = f'<a href="data:application/json;base64,{b64}" download="{filename}">Download {filename}</a>'
            return href
        
        # Export section
        st.subheader("Export Data")
        st.markdown("Save a backup of your project data as a JSON file. You can use this file to restore your data later.")
        
        # Format the data for export (same structure as used in save_data)
        export_data = {
            'projects': st.session_state.projects,
            'next_project_id_num': st.session_state.next_project_id_num
        }
        
        # Generate the download filename with a timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"project_manager_backup_{timestamp}.json"
        
        # Create and display the download link
        st.markdown(get_download_link(export_data, download_filename), unsafe_allow_html=True)
        
        # Import section
        st.subheader("Import Data")
        st.markdown("Restore your project data from a previously exported JSON file.")
        st.warning("Importing data will replace all current projects and tasks. Make sure to export your current data first if you want to keep it.")
        
        uploaded_file = st.file_uploader("Choose a JSON backup file", type="json", key="json_uploader")
        
        if uploaded_file is not None:
            # Read the JSON file
            try:
                content = uploaded_file.read()
                import_data = json.loads(content)
                
                if st.button("Confirm Import"):
                    try:
                        # Validate the imported data
                        if 'projects' not in import_data or 'next_project_id_num' not in import_data:
                            st.error("Invalid backup file format. The file doesn't contain required data structures.")
                        else:
                            # Update the session state with the imported data
                            st.session_state.projects = import_data['projects']
                            st.session_state.next_project_id_num = import_data['next_project_id_num']
                            
                            # Mark data as changed and save immediately
                            mark_data_changed()
                            save_data()
                            
                            st.success("Data successfully imported and saved!")
                            st.balloons()
                    except Exception as e:
                        st.error(f"Error importing data: {e}")
            except json.JSONDecodeError:
                st.error("Invalid JSON file. Please upload a valid JSON backup file.")
            except Exception as e:
                st.error(f"Error reading file: {e}")
        
        # Data migration utility
        st.subheader("Data Migration & Recovery")
        st.markdown("If you're experiencing issues with the pickle data file, you can convert your data to JSON format.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Save Current Data as JSON"):
                try:
                    # First ensure we save any pending changes to the pickle file
                    if st.session_state.data_changed:
                        save_data()
                    
                    # Save the current data to a JSON file
                    json_data = {
                        'projects': st.session_state.projects,
                        'next_project_id_num': st.session_state.next_project_id_num
                    }
                    
                    json_file = os.path.join(DATA_DIR, 'project_data_backup.json')
                    with open(json_file, 'w') as f:
                        json.dump(json_data, f, indent=4)
                    
                    st.success(f"Data successfully saved to JSON file: {json_file}")
                except Exception as e:
                    st.error(f"Error saving data to JSON: {e}")
        
        with col2:
            if st.button("Load Data from JSON Backup"):
                try:
                    json_file = os.path.join(DATA_DIR, 'project_data_backup.json')
                    
                    if os.path.exists(json_file):
                        with open(json_file, 'r') as f:
                            json_data = json.load(f)
                        
                        if 'projects' in json_data and 'next_project_id_num' in json_data:
                            st.session_state.projects = json_data['projects']
                            st.session_state.next_project_id_num = json_data['next_project_id_num']
                            
                            # Save to the pickle file
                            mark_data_changed()
                            save_data()
                            
                            st.success("Data successfully loaded from JSON backup and saved!")
                        else:
                            st.error("Invalid JSON backup format.")
                    else:
                        st.error(f"JSON backup file not found: {json_file}")
                except Exception as e:
                    st.error(f"Error loading from JSON backup: {e}")

    # --- Footer ---
    st.markdown("---")
    st.markdown("Simple Project Manager - Personal Use Only")
    st.caption(f"Data is saved locally to `{DATA_FILE}`")


# --- Gatekeeper: Decide whether to show login or main app ---
if not st.session_state.get('logged_in', False):
    display_login_form()
else:
    run_main_app()