import streamlit as st
import pickle
import os
from datetime import datetime, date
import pandas as pd
from dotenv import load_dotenv

# --- Must be the first Streamlit command ---
st.set_page_config(layout="wide")

# --- Load environment variables and global configs ---
load_dotenv()
DATA_FILE = 'project_data_v2.pkl'
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


def save_data():
    """Save project data to a pickle file."""
    print(f"DEBUG: Attempting to save data to {os.path.abspath(DATA_FILE)}...")
    # print(f"DEBUG: Data to be saved: {st.session_state.projects}") # Can be very verbose
    data_to_save = {
        'projects': st.session_state.projects,
        'next_project_id_num': st.session_state.next_project_id_num
    }
    try:
        with open(DATA_FILE, 'wb') as f:
            pickle.dump(data_to_save, f)
        print(f"DEBUG: Data successfully saved to {DATA_FILE}")
        st.toast(f"Data saved to {DATA_FILE}!", icon="💾")
    except Exception as e:
        print(f"DEBUG: ERROR SAVING DATA: {e}")
        st.error(f"Failed to save data: {e}")

def load_data():
    """Load project data from pickle file if it exists, then initialize state."""
    print(f"DEBUG: Attempting to load data from {os.path.abspath(DATA_FILE)}...")
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'rb') as f:
                loaded_data = pickle.load(f)
                st.session_state.projects = loaded_data.get('projects', {})
                st.session_state.next_project_id_num = loaded_data.get('next_project_id_num', 1)
                print(f"DEBUG: Data successfully loaded from {DATA_FILE}.")
                # print(f"DEBUG: Loaded projects: {st.session_state.projects}") # Verbose
                # print(f"DEBUG: Loaded next_project_id_num: {st.session_state.next_project_id_num}")
        except Exception as e:
            print(f"DEBUG: ERROR LOADING DATA from {DATA_FILE}: {e}. Initializing fresh state.")
            st.error(f"Error loading data file: {e}. Starting with a fresh state.")
            st.session_state.projects = {} # Ensure clean state on error
            st.session_state.next_project_id_num = 1
    else:
        print(f"DEBUG: Data file {DATA_FILE} not found. Initializing fresh state.")
    initialize_state() # Ensures all necessary session_state keys are present


# --- Initial Data Load and State Setup (runs once per session) ---
if not st.session_state.get('app_initialized', False):
    load_data() # This calls initialize_state() at its end
    st.session_state.app_initialized = True
else:
    # On subsequent reruns, ensure core state keys exist
    # This is a safeguard, initialize_state() is designed to be safe to call multiple times
    initialize_state()


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
            st.experimental_rerun() # Use experimental_rerun for cleaner state updates on login
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
        ["Projects Dashboard", "Add/Edit Project", "Manage Tasks"],
        key="navigation_page_main_app" # Unique key
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("Save All Data Manually"):
        save_data()
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.tasks_expanded = {} # Clear task expansion state on logout
        st.experimental_rerun() # Rerun to go back to login screen

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
                    st.markdown("#### Tasks")
                    if not project_details_selected['tasks']:
                        st.info("No tasks for this project yet. Go to 'Manage Tasks' to add some.")
                    else:
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
                submitted = st.form_submit_button("Create Project")
                if submitted:
                    if not project_name: st.error("Project name is required!")
                    else:
                        project_id = f"P{st.session_state.next_project_id_num}"
                        st.session_state.next_project_id_num += 1
                        st.session_state.projects[project_id] = {
                            'name': project_name, 'description': project_description,
                            'created_date': datetime.now().strftime("%Y-%m-%d"), 'tasks': []}
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
                        edit_submitted = st.form_submit_button("Update Project")
                        if edit_submitted:
                            if not edit_project_name: st.error("Project name cannot be empty!")
                            else:
                                st.session_state.projects[project_to_edit_id]['name'] = edit_project_name
                                st.session_state.projects[project_to_edit_id]['description'] = edit_project_description
                                save_data()
                                st.success(f"Project '{edit_project_name}' updated successfully!")
                                st.experimental_rerun()
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
                        save_data()
                        st.success(f"Project '{project_name_to_delete}' deleted successfully.")
                        st.experimental_rerun()

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
                                st.experimental_rerun()
                        if is_editing:
                            with cols[4]:
                                if st.button("💾", key=f"{task_key_prefix}_update", help="Save Task Changes"):
                                    if not new_name.strip(): st.error("Task name cannot be empty.")
                                    else:
                                        project_val['tasks'][i]['name'] = new_name
                                        project_val['tasks'][i]['due_date'] = new_due_date.strftime("%Y-%m-%d") if new_due_date else None
                                        project_val['tasks'][i]['status'] = new_status
                                        st.session_state.tasks_expanded[task_edit_state_key] = False
                                        save_data()
                                        st.success(f"Task '{new_name}' updated!")
                                        st.experimental_rerun()
                        else:
                            with cols[4]: st.empty()
                        with cols[5]:
                            if st.button("🗑️", key=f"{task_key_prefix}_delete", help="Delete Task"):
                                deleted_task_name = project_val['tasks'].pop(i)['name']
                                if task_edit_state_key in st.session_state.tasks_expanded:
                                    del st.session_state.tasks_expanded[task_edit_state_key]
                                save_data()
                                st.success(f"Task '{deleted_task_name}' deleted.")
                                st.experimental_rerun()
                        st.divider()
                else: st.info("No tasks for this project yet.")

                st.subheader("Add New Task")
                with st.form(f"add_task_form_{selected_project_id_tasks}_main_app", clear_on_submit=True): # Unique key
                    task_name = st.text_input("Task Name", key=f"new_task_name_{selected_project_id_tasks}_main_app")
                    task_due_date = st.date_input("Due Date", value=date.today(), key=f"new_task_due_{selected_project_id_tasks}_main_app")
                    task_status = st.selectbox("Status", ["Not Started", "In Progress", "Completed", "Blocked"],
                                               key=f"new_task_status_{selected_project_id_tasks}_main_app")
                    add_task_submitted = st.form_submit_button("Add Task") # Corrected typo here
                    if add_task_submitted:
                        if not task_name: st.error("Task name is required!")
                        else:
                            project_val['tasks'].append({
                                'name': task_name, 'due_date': task_due_date.strftime("%Y-%m-%d") if task_due_date else None,
                                'status': task_status })
                            save_data()
                            st.success(f"Task '{task_name}' added to '{project_val['name']}'!")
                            st.experimental_rerun()

    # --- Footer ---
    st.markdown("---")
    st.markdown("Simple Project Manager - Personal Use Only")
    st.caption(f"Data is saved locally to `{os.path.abspath(DATA_FILE)}`")


# --- Gatekeeper: Decide whether to show login or main app ---
if not st.session_state.get('logged_in', False):
    display_login_form()
else:
    run_main_app()