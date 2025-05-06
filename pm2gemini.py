import streamlit as st
import pickle
import os
from datetime import datetime, date
import pandas as pd
from dotenv import load_dotenv # Import python-dotenv

# --- Load environment variables from .env file ---
load_dotenv() # This will load variables from your .env file

# --- Configuration ---
DATA_FILE = 'project_data_v2.pkl'

# --- !!! IMPORTANT: Password is now read from an environment variable !!! ---
# The variable name in your .env file should be PROJECT_APP_PASSWORD
APP_PASSWORD = os.environ.get("PROJECT_APP_PASSWORD")

# --- Data Persistence ---
def initialize_state():
    """Initialize session state variables if they don't exist."""
    if 'projects' not in st.session_state:
        st.session_state.projects = {}
    if 'next_project_id_num' not in st.session_state:
        st.session_state.next_project_id_num = 1
    if 'tasks_expanded' not in st.session_state:
        st.session_state.tasks_expanded = {}
    # Add login state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

def save_data():
    """Save project data to a pickle file."""
    data_to_save = {
        'projects': st.session_state.projects,
        'next_project_id_num': st.session_state.next_project_id_num
    }
    with open(DATA_FILE, 'wb') as f:
        pickle.dump(data_to_save, f)

def load_data():
    """Load project data from pickle file if it exists."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'rb') as f:
            try:
                loaded_data = pickle.load(f)
                st.session_state.projects = loaded_data.get('projects', {})
                st.session_state.next_project_id_num = loaded_data.get('next_project_id_num', 1)
            except Exception as e:
                st.error(f"Error loading data file: {e}. Starting with a fresh state.")
                st.session_state.projects = {}
                st.session_state.next_project_id_num = 1
    initialize_state()

# --- Password Protection ---
def check_password():
    """Returns True if the user has entered the correct password."""
    global APP_PASSWORD # Ensure we are using the global APP_PASSWORD loaded from env

    if APP_PASSWORD is None: # Check if the password was loaded from environment
        st.error("CRITICAL: Application password not configured. Please set the 'PROJECT_APP_PASSWORD' environment variable or in your .env file.")
        st.info("If running locally, create a '.env' file in the app directory with: PROJECT_APP_PASSWORD='yourpassword'")
        return False # Cannot proceed without a password to check against

    if st.session_state.get("logged_in", False):
        return True

    st.title("Login Required")
    st.write("Please enter the password to access the Project Manager.")

    password_attempt = st.text_input("Password", type="password", key="password_input_main")
    if st.button("Login", key="login_button_main"):
        if password_attempt == APP_PASSWORD:
            st.session_state.logged_in = True
            st.rerun() # Rerun to reflect login state immediately
        else:
            st.error("Incorrect password. Please try again.")
    return False

# --- Helper Functions ---
def get_project_display_name(project_id):
    if project_id in st.session_state.projects:
        return f"{project_id}: {st.session_state.projects[project_id]['name']}"
    return project_id

# --- Initialize and Load ---
load_data() # Load data first, then check password

# --- Main App Logic - only if logged in ---
if not check_password():
    st.stop() # Stop execution if not logged in or password not configured

# If we reach here, the user is logged in, and APP_PASSWORD was found.
st.set_page_config(layout="wide") # This should be the first Streamlit command if not conditional
st.title("Personal Project Manager")
st.markdown("Manage your personal projects and tasks effectively.")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Projects Dashboard", "Add/Edit Project", "Manage Tasks"],
    key="navigation_page"
)
st.sidebar.markdown("---")
if st.sidebar.button("Save All Data Manually"):
    save_data()
    st.sidebar.success("Data saved!")
if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.tasks_expanded = {} # Clear task expansion state on logout
    # Potentially clear other sensitive session states if needed
    st.rerun()


# --- Page: Projects Dashboard ---
if page == "Projects Dashboard":
    st.header("Projects Dashboard")

    if not st.session_state.projects:
        st.info("No projects yet. Go to 'Add/Edit Project' to create one!")
    else:
        project_data = []
        for project_id, project in st.session_state.projects.items():
            total_tasks = len(project['tasks'])
            completed_tasks = sum(1 for task in project['tasks'] if task['status'] == 'Completed')
            progress = 0 if total_tasks == 0 else round((completed_tasks / total_tasks) * 100)

            project_data.append({
                'ID': project_id,
                'Name': project['name'],
                'Description': project['description'][:50] + '...' if len(project['description']) > 50 else project['description'],
                'Created': project['created_date'],
                'Tasks': total_tasks,
                'Progress': f"{progress}%"
            })

        if project_data:
            df = pd.DataFrame(project_data)
            st.dataframe(df, use_container_width=True)

            st.subheader("Project Details & Tasks")
            project_ids = list(st.session_state.projects.keys())
            selected_project_id_dashboard = st.selectbox(
                "Select a project to view details",
                options=project_ids,
                format_func=get_project_display_name,
                key="dashboard_project_select"
            )

            if selected_project_id_dashboard and selected_project_id_dashboard in st.session_state.projects:
                project = st.session_state.projects[selected_project_id_dashboard]
                st.markdown(f"### {project['name']} (`{selected_project_id_dashboard}`)")
                st.markdown(f"**Description:** {project['description']}")
                st.markdown(f"**Created:** {project['created_date']}")

                st.markdown("#### Tasks")
                if not project['tasks']:
                    st.info("No tasks for this project yet. Go to 'Manage Tasks' to add some.")
                else:
                    task_list_data = []
                    for i, task in enumerate(project['tasks']):
                        task_list_data.append({
                            '#': i + 1,
                            'Task': task['name'],
                            'Due Date': task['due_date'],
                            'Status': task['status']
                        })
                    st.table(pd.DataFrame(task_list_data).set_index('#'))
        else:
            st.info("No projects available to display.")

# --- Page: Add/Edit Project ---
elif page == "Add/Edit Project":
    st.header("Add or Edit Project")

    action = st.radio("Select Action", ["Create New Project", "Edit Existing Project", "Delete Project"], key="project_action_radio", horizontal=True)

    if action == "Create New Project":
        st.subheader("Create New Project")
        with st.form("new_project_form", clear_on_submit=True):
            project_name = st.text_input("Project Name", key="new_proj_name")
            project_description = st.text_area("Project Description", key="new_proj_desc")
            submitted = st.form_submit_button("Create Project")

            if submitted:
                if not project_name:
                    st.error("Project name is required!")
                else:
                    project_id = f"P{st.session_state.next_project_id_num}"
                    st.session_state.next_project_id_num += 1
                    st.session_state.projects[project_id] = {
                        'name': project_name,
                        'description': project_description,
                        'created_date': datetime.now().strftime("%Y-%m-%d"),
                        'tasks': []
                    }
                    save_data()
                    st.success(f"Project '{project_name}' created successfully with ID: {project_id}")
                    st.balloons()

    elif action == "Edit Existing Project":
        st.subheader("Edit Existing Project")
        if not st.session_state.projects:
            st.info("No projects to edit. Create one first.")
        else:
            project_ids = list(st.session_state.projects.keys())
            project_to_edit_id = st.selectbox(
                "Select Project to Edit",
                options=project_ids,
                format_func=get_project_display_name,
                key="edit_project_select"
            )

            if project_to_edit_id:
                project_data = st.session_state.projects[project_to_edit_id]
                # Use a unique key for the form to ensure it resets if the selected project changes
                with st.form(f"edit_project_form_{project_to_edit_id}"):
                    st.markdown(f"Editing Project ID: **{project_to_edit_id}**")
                    edit_project_name = st.text_input(
                        "Project Name",
                        value=project_data['name'],
                        key=f"edit_proj_name_{project_to_edit_id}"
                    )
                    edit_project_description = st.text_area(
                        "Project Description",
                        value=project_data['description'],
                        key=f"edit_proj_desc_{project_to_edit_id}"
                    )
                    edit_submitted = st.form_submit_button("Update Project")

                    if edit_submitted:
                        if not edit_project_name:
                            st.error("Project name cannot be empty!")
                        else:
                            st.session_state.projects[project_to_edit_id]['name'] = edit_project_name
                            st.session_state.projects[project_to_edit_id]['description'] = edit_project_description
                            save_data()
                            st.success(f"Project '{edit_project_name}' updated successfully!")
                            st.rerun()

    elif action == "Delete Project":
        st.subheader("Delete Project")
        if not st.session_state.projects:
            st.info("No projects to delete.")
        else:
            project_ids = list(st.session_state.projects.keys())
            project_to_delete_id = st.selectbox(
                "Select Project to Delete",
                options=project_ids,
                format_func=get_project_display_name,
                key="delete_project_select"
            )

            if project_to_delete_id:
                project_name_to_delete = st.session_state.projects[project_to_delete_id]['name']
                st.warning(f"Are you sure you want to delete project '{project_name_to_delete}' ({project_to_delete_id})? This action cannot be undone and will delete all associated tasks.")

                # Ensure unique key for delete confirmation button
                if st.button(f"Yes, Delete Project '{project_name_to_delete}'", key=f"confirm_delete_btn_{project_to_delete_id}"):
                    del st.session_state.projects[project_to_delete_id]
                    keys_to_del = [k for k in st.session_state.tasks_expanded if k.startswith(project_to_delete_id)]
                    for k_del in keys_to_del:
                        del st.session_state.tasks_expanded[k_del]
                    save_data()
                    st.success(f"Project '{project_name_to_delete}' deleted successfully.")
                    st.rerun()


# --- Page: Manage Tasks ---
elif page == "Manage Tasks":
    st.header("Manage Tasks")

    if not st.session_state.projects:
        st.info("No projects yet. Go to 'Add/Edit Project' to create a project first.")
    else:
        project_ids = list(st.session_state.projects.keys())
        selected_project_id_tasks = st.selectbox(
            "Select Project",
            options=project_ids,
            format_func=get_project_display_name,
            key="manage_tasks_project_select"
        )

        if selected_project_id_tasks:
            project = st.session_state.projects[selected_project_id_tasks]
            st.subheader(f"Tasks for: {project['name']} (`{selected_project_id_tasks}`)")

            if project['tasks']:
                for i, task in enumerate(project['tasks']):
                    task_key_prefix = f"task_{selected_project_id_tasks}_{i}"
                    task_edit_state_key = f"{selected_project_id_tasks}_{i}" # Used for st.session_state.tasks_expanded

                    cols = st.columns([3, 2, 2, 0.8, 0.8, 0.8])

                    with cols[0]: # Task Name
                        if st.session_state.tasks_expanded.get(task_edit_state_key, False):
                            new_name = st.text_input("Name", value=task['name'], key=f"{task_key_prefix}_name_edit", label_visibility="collapsed")
                        else:
                            st.markdown(f"**{i+1}. {task['name']}**")
                    with cols[1]: # Due Date
                        if st.session_state.tasks_expanded.get(task_edit_state_key, False):
                            try:
                                current_due_date = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                            except ValueError:
                                current_due_date = date.today()
                            new_due_date = st.date_input("Due", value=current_due_date, key=f"{task_key_prefix}_due_edit", label_visibility="collapsed")
                        else:
                            st.markdown(task['due_date'])
                    with cols[2]: # Status
                        if st.session_state.tasks_expanded.get(task_edit_state_key, False):
                            status_options = ["Not Started", "In Progress", "Completed", "Blocked"]
                            current_status_idx = status_options.index(task['status']) if task['status'] in status_options else 0
                            new_status = st.selectbox(
                                "Status", options=status_options, index=current_status_idx,
                                key=f"{task_key_prefix}_status_edit", label_visibility="collapsed"
                            )
                        else:
                            st.markdown(task['status'])

                    with cols[3]: # Edit Toggle Button
                        if st.button("✏️" if not st.session_state.tasks_expanded.get(task_edit_state_key, False) else "🔽", key=f"{task_key_prefix}_toggle_edit", help="Edit Task" if not st.session_state.tasks_expanded.get(task_edit_state_key, False) else "Collapse Edit"):
                            st.session_state.tasks_expanded[task_edit_state_key] = not st.session_state.tasks_expanded.get(task_edit_state_key, False)
                            st.rerun()

                    if st.session_state.tasks_expanded.get(task_edit_state_key, False):
                        with cols[4]: # Update Button
                            if st.button("💾", key=f"{task_key_prefix}_update", help="Save Task Changes"):
                                if not new_name.strip():
                                    st.error("Task name cannot be empty.")
                                else:
                                    project['tasks'][i]['name'] = new_name
                                    project['tasks'][i]['due_date'] = new_due_date.strftime("%Y-%m-%d")
                                    project['tasks'][i]['status'] = new_status
                                    st.session_state.tasks_expanded[task_edit_state_key] = False # Collapse after save
                                    save_data()
                                    st.success(f"Task '{new_name}' updated!")
                                    st.rerun()
                    else:
                        with cols[4]: st.empty()

                    with cols[5]: # Delete Button
                        if st.button("🗑️", key=f"{task_key_prefix}_delete", help="Delete Task"):
                            deleted_task_name = project['tasks'].pop(i)['name']
                            if task_edit_state_key in st.session_state.tasks_expanded:
                                del st.session_state.tasks_expanded[task_edit_state_key]
                            save_data()
                            st.success(f"Task '{deleted_task_name}' deleted.")
                            st.rerun()
                    st.divider()
            else:
                st.info("No tasks for this project yet.")

            st.subheader("Add New Task")
            with st.form(f"add_task_form_{selected_project_id_tasks}", clear_on_submit=True):
                task_name = st.text_input("Task Name", key=f"new_task_name_{selected_project_id_tasks}")
                task_due_date = st.date_input("Due Date", value=date.today(), key=f"new_task_due_{selected_project_id_tasks}")
                task_status = st.selectbox("Status", ["Not Started", "In Progress", "Completed", "Blocked"], key=f"new_task_status_{selected_project_id_tasks}")
                add_task_submitted = st.form_submit_button("Add Task")

                if add_task_submitted:
                    if not task_name:
                        st.error("Task name is required!")
                    else:
                        project['tasks'].append({
                            'name': task_name,
                            'due_date': task_due_date.strftime("%Y-%m-%d"),
                            'status': task_status
                        })
                        save_data()
                        st.success(f"Task '{task_name}' added to '{project['name']}'!")
                        st.rerun()

# --- Footer ---
st.markdown("---")
st.markdown("Simple Project Manager - Personal Use Only")
st.caption(f"Data is saved locally to `{DATA_FILE}`")