import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
from real_estate_listings import RealEstateListingApp
from taskbreaker import AgentHead
import datetime
import requests
import winsound
import uuid
import json
import os

# Utility functions for JSON handling
def load_json_file(filename, default_value=None):
    try:
        with open(filename, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_value if default_value is not None else []

def save_json_to_file(data, filename):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4)
        
def todoist_read_tasks(api_token, sync_token='*'):
    """
    Fetch tasks from Todoist using the Sync API.

    :param api_token: Your Todoist API token.
    :param sync_token: Sync token for incremental synchronization, '*' for initial sync.
    :return: Tuple of (new sync_token, tasks)
    """
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {"Authorization": f"Bearer {api_token}"}
    data = {
        "sync_token": sync_token,
        "resource_types": '["items"]'
    }

    response = requests.post(url, headers=headers, data=data)
    response_data = response.json()

    new_sync_token = response_data.get("sync_token", "")
    tasks = response_data.get("items", [])

    return new_sync_token, tasks

def create_todoist_task(api_token, task_name, project_id=None):
    """
    Create a new task in Todoist and return the command UUID.

    :param api_token: Todoist API token.
    :param task_name: Name of the task to create.
    :param project_id: Optional project ID to assign the task to.
    :return: UUID of the command used to create the task.
    """
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {"Authorization": f"Bearer {api_token}"}
    command_uuid = str(uuid.uuid4())  # Generate a unique command UUID
    command = {
        "type": "item_add",
        "temp_id": str(uuid.uuid4()),  # Generate a unique temporary ID
        "uuid": command_uuid,  # Use the generated command UUID
        "args": {
            "content": task_name,
            "project_id": project_id
        }
    }

    data = {
        "commands": json.dumps([command])
    }

    requests.post(url, headers=headers, data=data)  # Execute the request
    return command_uuid  # Return the command UUID


def complete_todoist_task(api_token, task_id):
    """
    Mark a task as complete in Todoist.

    :param api_token: Todoist API token.
    :param task_id: The ID of the task to mark as complete.
    :return: Response from the API call.
    """
    url = "https://api.todoist.com/sync/v9/sync"
    headers = {"Authorization": f"Bearer {api_token}"}
    command = {
        "type": "item_close",
        "uuid": str(uuid.uuid4()),
        "args": {
            "id": task_id
        }
    }

    data = {
        "commands": json.dumps([command])
    }

    response = requests.post(url, headers=headers, data=data)
    return response.json()
# Productivity Timer Application
class ProductivityTimerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Productivity Timer")
        self.reminder_interval = tk.IntVar(value=5)  # Default to 5 minutes
        self.last_beep_second = -1  # Initialize with a value that ensures the first second will trigger a beep
        self.last_beep_time = datetime.datetime.min  # Initialize with a minimal datetime
        self.local_unsynced_tasks = []  # To store tasks created while offline
        self.is_sound_muted = False
        self.task_breaker = AgentHead(n_breakups=5)  # Adjust the number as needed
        self.task_name_to_id_map = {}  # Initialize the mapping
        self.command_uuid_to_task_map = {}  # Initialize the command UUID to task mapping
 #       self.delete_task_button = tk.Button(root, text="Delete Current Task", command=self.delete_current_task)
 #       self.delete_task_button.pack()
        # Next task button
        self.root = root
        self.root.title("Productivity Timer")
        self.root.geometry("600x400")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha', 0.85)
        self.file_path_var = tk.StringVar()
        self.initialize_variables()
        self.create_widgets()
        self.load_state()
        self.update_timer_display()

    def break_down_task(self):
        # Use the current active task for breakdown
        if self.task_name:
            sub_tasks = self.task_breaker.generate_response(self.task_name)
            self.show_sub_tasks(sub_tasks)
        else:
            messagebox.showinfo("No Active Task", "Please select a task to break down.")

    def show_sub_tasks(self, sub_tasks):
        # Method to display sub-tasks
        sub_task_window = tk.Toplevel(self.root)
        sub_task_window.title("Sub-tasks")
        tk.Label(sub_task_window, text=sub_tasks).pack()
        close_button = tk.Button(sub_task_window, text="Close", command=sub_task_window.destroy)
        close_button.pack()

    def move_task_to_top(self):
        """
        Move the highlighted task to the top of the list, except the active task.
        """
        selected_index = self.tasks_listbox.curselection()

        # Check if a task is selected and it's not the active task
        if selected_index and (selected_index[0] != 0 or not self.task_name):
            # Move the selected task to the top of the list
            task_to_move = self.tasks.pop(selected_index[0])
            self.tasks.insert(0, task_to_move)

            # Update the tasks listbox
            self.update_tasks_listbox()
            # Select the moved task in the listbox
            self.tasks_listbox.select_set(0)
        else:
            messagebox.showinfo("Info", "Please select a non-active task to move.")
    def print_todays_tasks(self):
        """
        Print all tasks.
        """
        print("Current Tasks:")
        for task in self.tasks:
            print(task)
        
    def get_todoist_task_id(self, task_name):
        """
        Return the Todoist task ID for the given task name.
        This requires maintaining a mapping of task names to IDs.
        """
        return self.task_name_to_id_map.get(task_name)

    
    def fetch_todoist_tasks(self):
        """Fetch tasks from Todoist using Sync API and update the application."""
        api_token = 'ff433257564136ab0e653cefe8988c61f58afd52'  # Your Todoist API token

        # Sync local unsynced tasks to Todoist
        for task in self.local_unsynced_tasks:
            try:
                create_todoist_task(api_token, task)
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to add task to Todoist: {e}")

        # Clear the local unsynced tasks list
        self.local_unsynced_tasks.clear()

        try:
            # Fetch tasks from Todoist
            sync_token = '*'  # Use '*' for the initial sync
            new_sync_token, fetched_tasks = todoist_read_tasks(api_token, sync_token)

            # Update the mapping of task names to Todoist IDs
            fetched_task_contents = {task['content']: task['id'] for task in fetched_tasks}
            self.task_name_to_id_map.update(fetched_task_contents)

            # Update the local task list and mapping with active tasks from Todoist
            self.tasks.clear()
            self.task_name_to_id_map.clear()

            for task in fetched_tasks:
                task_content = task['content']
                task_id = task['id']
                self.tasks.append(task_content)
                self.task_name_to_id_map[task_content] = task_id

            # Update the tasks in the JSON file and the listbox
            save_json_to_file(self.tasks, self.task_list_file)
            self.update_tasks_listbox()

            # Optionally, store the new_sync_token for future use

        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to fetch tasks from Todoist: {e}")

    def delete_todoist_task(api_token, task_id):
        """
        Delete a task in Todoist.

        :param api_token: Todoist API token.
        :param task_id: The ID of the task to delete.
        :return: Response from the API call.
        """
        url = "https://api.todoist.com/sync/v9/sync"
        headers = {"Authorization": f"Bearer {api_token}"}
        command = {
            "type": "item_delete",
            "uuid": str(uuid.uuid4()),
            "args": {
                "id": task_id
            }
        }

        data = {
            "commands": json.dumps([command])
        }

        response = requests.post(url, headers=headers, data=data)
        return response.json()

    def delete_current_task(self):
        if self.task_name:
            todoist_task_id = self.get_todoist_task_id(self.task_name)
            print(f"Deleting task: {self.task_name} with Todoist ID: {todoist_task_id}")  # Logging for debugging
            if todoist_task_id:
                try:
                    response = delete_todoist_task('ff433257564136ab0e653cefe8988c61f58afd52', todoist_task_id)
                    print(f"Response from Todoist: {response}")  # Logging the response
                    self.tasks.remove(self.task_name)
                    del self.task_name_to_id_map[self.task_name]
                    self.task_name = None
                    self.update_tasks_listbox()
                    self.reset_timer()
                    self.update_task_label()
                except requests.RequestException as e:
                    messagebox.showerror("Error", f"Failed to delete task in Todoist: {e}")
                    print(f"Error deleting task in Todoist: {e}")  # Logging the error

    def toggle_sound(self):
        self.is_sound_muted = not self.is_sound_muted
        self.mute_button.config(text="Unmute" if self.is_sound_muted else "Mute")

    def initialize_variables(self):
        self.running = False
        self.start_time = None
        self.task_name = None
        self.task_list_file = "tasks.json"
        self.tasks = load_json_file(self.task_list_file, [])
        self.total_seconds = 0

    def create_widgets(self):
        # Frame for buttons
        self.buttons_frame = tk.Frame(self.root)
        self.buttons_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Configure grid layout for buttons_frame
        n_columns = 6
        for i in range(n_columns):
            self.buttons_frame.grid_columnconfigure(i, weight=1)

        self.create_button("Break Down Task", self.break_down_task, 0, 0)
        self.create_button("Print Today's Tasks", self.print_todays_tasks, 1, 0)
        self.create_button("Start", self.start_or_complete_task, 2, 0)
        self.create_button("Pause", self.toggle_pause, 0, 1, tk.DISABLED)
        self.create_button("Reset Timer", self.reset_current_task_timer, 1, 1)
        self.create_button("Mute", self.toggle_sound, 2, 1)

        # Reminder interval label and dropdown
        self.reminder_interval_label = tk.Label(self.buttons_frame, text="Reminder Interval (minutes):")
        self.reminder_interval_label.grid(row=0, column=0, sticky=tk.W)
        self.reminder_interval_dropdown = tk.OptionMenu(self.buttons_frame, self.reminder_interval, 5, 10, 15, 20, 30, 60)
        self.reminder_interval_dropdown.grid(row=0, column=1, sticky=tk.W)

        # Other buttons
        self.break_task_button = tk.Button(self.buttons_frame, text="Break Down Task", command=self.break_down_task)
        self.break_task_button.grid(row=0, column=2)
        self.print_button = tk.Button(self.buttons_frame, text="Print Today's Tasks", command=self.print_todays_tasks)
        self.print_button.grid(row=0, column=3)
        self.start_button = tk.Button(self.buttons_frame, text="Start", command=self.start_or_complete_task)
        self.start_button.grid(row=0, column=4)
        self.pause_button = tk.Button(self.buttons_frame, text="Pause", command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.grid(row=0, column=5)
        self.reset_timer_button = tk.Button(self.buttons_frame, text="Reset Timer", command=self.reset_current_task_timer)
        self.reset_timer_button.grid(row=0, column=6)
        self.mute_button = tk.Button(self.buttons_frame, text="Mute", command=self.toggle_sound)
        self.mute_button.grid(row=0, column=7)
        self.add_task_button = tk.Button(self.buttons_frame, text="Add Task", command=self.add_task)
        self.add_task_button.grid(row=0, column=8)
        self.swap_task_button = tk.Button(self.buttons_frame, text="Swap Active Task", command=self.swap_active_task)
        self.swap_task_button.grid(row=0, column=9)
        self.fetch_tasks_button = tk.Button(self.buttons_frame, text="Fetch Todoist Tasks", command=self.fetch_todoist_tasks)
        self.fetch_tasks_button.grid(row=0, column=10)

        # Timer label
        self.timer_label = tk.Label(self.root, text="00:00:00", font=("Helvetica", 48))
        self.timer_label.pack(pady=(10, 0))

        # Task label
        self.task_label = tk.Label(self.root, text="Task: None", font=("Helvetica", 24))
        self.task_label.pack(pady=(10, 20))

        # Listbox for tasks
        self.tasks_listbox = tk.Listbox(self.root)
        self.tasks_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.update_tasks_listbox()

        # Up and Down arrow buttons
        self.move_up_button = tk.Button(self.root, text="↑", command=self.move_task_up)
        self.move_up_button.pack(side=tk.RIGHT, padx=5)
        self.move_down_button = tk.Button(self.root, text="↓", command=self.move_task_down)
        self.move_down_button.pack(side=tk.RIGHT, padx=5)
    
    def create_button(self, text, command, col, row, state=tk.NORMAL):
        button = tk.Button(self.buttons_frame, text=text, command=command, state=state)
        button.grid(column=col, row=row, sticky="ew", padx=5, pady=5)
    
    def start_or_complete_task(self):
        if not self.running:
            if not self.tasks:
                messagebox.showwarning("No Tasks", "No tasks available to start.")
                return
            self.task_name = self.tasks.pop(0)
            self.start_time = datetime.datetime.now()
            self.running = True
            self.start_button.config(text="Complete Task")
            self.pause_button.config(state=tk.NORMAL)
            self.update_task_label()
            self.update_tasks_listbox()
        else:
            self.complete_task()
  
    def toggle_pause(self):
        if not self.running and self.task_name:
            self.running = True
            self.start_time = datetime.datetime.now() - datetime.timedelta(seconds=self.total_seconds)
            self.pause_button.config(text="Pause")
            self.update_timer_display()
        else:
            self.running = not self.running
            self.pause_button.config(text="Resume" if not self.running else "Pause")


    def update_timer_display(self):
        if self.running and self.task_name:  # Check if a task is active and the timer is running
            current_time = datetime.datetime.now()
            elapsed_time = current_time - self.start_time
            self.total_seconds = int(elapsed_time.total_seconds())
            self.timer_label.config(text=str(elapsed_time).split('.')[0])

            if not self.is_sound_muted and (current_time - self.last_beep_time).total_seconds() >= 1:
                try:
                    winsound.Beep(1000, 100)  # Beep sound
                    self.last_beep_time = current_time  # Update the last beep time
                except RuntimeError:
                    pass  # Ignore if the beep command fails or overlaps

        self.root.after(1000, self.update_timer_display)  # Schedule the next update

    def prompt_stay_on_track(self):
        response = messagebox.askyesno("Stay on Track", "Are you still working on the task?")
        if not response:
            reason = simpledialog.askstring("Reason", "Why did you not finish the task?")
            self.log_incompletion(reason)
            
            # Ask if the task should be moved to the bottom of the list
            if messagebox.askyesno("Task Requeue", "Do you want to move this task to the bottom of the list?"):
                self.tasks.append(self.task_name)
                self.update_tasks_listbox()
                self.start_or_complete_task()  # Optionally start the next task immediately

    def log_incompletion(self, reason):
        with open("productivity_log.txt", "a") as file:
            file.write(f"Task Incompletion Reason: {reason}\n")
        def play_beep(self):
            try:
                winsound.Beep(1000, 100)  # Beep sound for 100 milliseconds
            except RuntimeError:
                pass  # Ignore if the previous beep is still playing

    def add_task(self):
        new_task = simpledialog.askstring("New Task", "Enter the new task:")
        if new_task:
            self.tasks.append(new_task)
            self.update_tasks_listbox()
            save_json_to_file(self.tasks, self.task_list_file)

            # Create the task in Todoist and store the command UUID
            api_token = 'ff433257564136ab0e653cefe8988c61f58afd52'  # Your Todoist API token
            try:
                command_uuid = create_todoist_task(api_token, new_task)
                # Store the command UUID against the new task name for future mapping after sync
                self.command_uuid_to_task_map[command_uuid] = new_task
                # Note: Ensure `self.command_uuid_to_task_map` is initialized in the constructor (__init__ method)
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to add task to Todoist: {e}")
            
                
    def add_task_from_completion_window(self):
        # Example implementation of adding a task from the completion window
        new_task = simpledialog.askstring("New Task", "Enter the name of the new task:")
        if new_task:
            self.tasks.append(new_task)
            self.update_tasks_listbox()
            save_json_to_file(self.tasks, self.task_list_file)

    def save_and_close_completion_window(self):
        # Save the data from the completion window
        client_name = self.client_name_var.get()
        project_notes = self.project_notes_var.get()
        selected_file_path = self.file_path_var.get() if hasattr(self, 'file_path_var') else ""

        # Here, you can process the saved data as needed
        # For example, log them to a file or update any relevant UI components

        # Close the completion window
        self.completion_window.destroy()

    def complete_task(self):
        # Log and update UI before marking the task as complete
        self.log_task()
        completed_task_name = self.task_name
        self.running = False
        self.start_button.config(text="Start")
        self.pause_button.config(state=tk.DISABLED)
        self.timer_label.config(text="00:00:00")
        self.total_seconds = 0
        self.task_name = None
        self.show_completion_window()
        self.update_task_label()

        # Start the next task if available
        if self.tasks:
            self.start_or_complete_task()

        # Mark the task as complete in Todoist
        api_token = 'ff433257564136ab0e653cefe8988c61f58afd52'  # Replace with your Todoist API token
        todoist_task_id = self.get_todoist_task_id(completed_task_name)
        
        if todoist_task_id:
            try:
                complete_todoist_task(api_token, todoist_task_id)
                # Remove the completed task from local tasks and ID map
                self.tasks.remove(completed_task_name)
                del self.task_name_to_id_map[completed_task_name]
                self.update_tasks_listbox()
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to complete task in Todoist: {e}")
                
    def log_task(self):
        # Get the file path. If none selected, log 'No file selected'
        selected_file_path = self.file_path_var.get() if self.file_path_var.get() else "No file selected"
        log_msg = f"Task: {self.task_name}\nStart Time: {self.start_time}\nEnd Time: {datetime.datetime.now()}\nFile Path: {selected_file_path}\n"
        
        with open("productivity_log.txt", "a") as log_file:
            log_file.write(log_msg)

        # Reset file path variable after logging
        self.file_path_var.set("")

    def reset_timer(self):
        # Reset the timer logic
        self.running = False
        self.total_seconds = 0
        self.last_beep_second = -1  # If you are using this for sound control
        self.timer_label.config(text="00:00:00")
        # Add any other logic needed to reset the timer
    def reset_current_task_timer(self):
        """
        Reset the timer for the current task without completing it.
        """
        if self.task_name:
            self.running = False  # Stop the current timer
            self.total_seconds = 0  # Reset the elapsed seconds to zero
            self.start_time = None  # Clear the start time
            self.timer_label.config(text="00:00:00")  # Reset the timer label
            self.pause_button.config(state=tk.NORMAL, text="Resume")  # Enable and set the pause button text to "Resume"
            self.start_button.config(text="Start")  # Change the start button text back to "Start"

            # Optional: Display a message indicating the timer has been reset
            messagebox.showinfo("Timer Reset", "The timer has been reset.")
        else:
            messagebox.showinfo("Info", "No active task to reset.")

    def select_file_or_folder(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path_var.set(file_path)  # Store the selected file path

    def update_task_label(self):
        self.task_label.config(text=f"Task: {self.task_name if self.task_name else 'None'}")

    def update_tasks_listbox(self):
        self.tasks_listbox.delete(0, tk.END)
        for task in self.tasks:
            self.tasks_listbox.insert(tk.END, task)

    def backup_tasks(self):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"task_backup_{timestamp}.json"
        save_json_to_file(self.tasks, backup_filename)

    def load_state(self):
        state_file = 'current_state.json'
        if os.path.exists(state_file):
            with open(state_file, 'r') as file:
                state = json.load(file)
            self.task_name = state.get('task_name')
            self.start_time = datetime.datetime.strptime(state['start_time'], "%Y-%m-%d %H:%M:%S")
            self.total_seconds = state['total_seconds']
            self.running = True
            self.start_button.config(text="Complete Task")
            self.pause_button.config(state=tk.NORMAL)
            self.update_task_label()

    def move_task_up(self):
        selected = self.tasks_listbox.curselection()
        if selected:
            index = selected[0]
            if index > 0:
                self.tasks.insert(index - 1, self.tasks.pop(index))
                self.update_tasks_listbox()
                self.tasks_listbox.select_set(index - 1)  # Keep the item selected

    def move_task_down(self):
        selected = self.tasks_listbox.curselection()
        if selected:
            index = selected[0]
            if index < len(self.tasks) - 1:
                self.tasks.insert(index + 1, self.tasks.pop(index))
                self.update_tasks_listbox()
                self.tasks_listbox.select_set(index + 1)  # Keep the item selected

    def show_completion_window(self):
        self.completion_window = tk.Toplevel(self.root)
        self.completion_window.title("Task Completion")

        # Client name input
        self.client_name_var = tk.StringVar()
        tk.Label(self.completion_window, text="Client Name:").pack()
        tk.Entry(self.completion_window, textvariable=self.client_name_var).pack()

        # Project notes
        self.project_notes_var = tk.StringVar()
        tk.Label(self.completion_window, text="Project Notes:").pack()
        tk.Entry(self.completion_window, textvariable=self.project_notes_var).pack()

        # File/Folder selection button
        self.file_path_var = tk.StringVar()
        tk.Button(self.completion_window, text="Add File/Folder", command=self.select_file_or_folder).pack()
        tk.Label(self.completion_window, textvariable=self.file_path_var).pack()

        # Add task button
        tk.Button(self.completion_window, text="Add Task", command=self.add_task_from_completion_window).pack()

        # Save/Close button
        tk.Button(self.completion_window, text="Save and Close", command=self.save_and_close_completion_window).pack()

    def select_file_or_folder(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path_var.set(file_path)  # Display the selected file path
        def on_closing(self):
            if self.running:
                current_state = {
                    'task_name': self.task_name,
                    'start_time': self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    'total_seconds': self.total_seconds
                }
                with open('current_state.json', 'w') as file:
                    json.dump(current_state, file)
            self.root.destroy()
                
    def swap_active_task(self):
        if self.task_name and self.tasks:
            selected_index = self.tasks_listbox.curselection()
            
            # Check if a task is selected in the listbox
            if selected_index:
                selected_index = selected_index[0]
                selected_task = self.tasks[selected_index]

                # Swap the active task with the selected task
                self.tasks[selected_index] = self.task_name
                self.task_name = selected_task

                # Update the task listbox and the task label
                self.update_tasks_listbox()
                self.update_task_label()

                # Move the listbox selection to the position of the now-active task
                self.tasks_listbox.select_clear(0, tk.END)
                self.tasks_listbox.select_set(selected_index)

                # Optionally save the updated tasks to a file
                save_json_to_file(self.tasks, self.task_list_file)
            else:
                messagebox.showinfo("Info", "Please select a task to swap with.")
        else:
            messagebox.showinfo("Info", "No active task to swap.")

    def load_next_task(self):
        if not self.task_name and self.tasks:
            # If there is no current task, set the next task from the list
            self.task_name = self.tasks.pop(0)
            self.update_task_label()
            self.start_timer()  # Assuming you have a method to start the timer for the new task

            # Update your task list display, if applicable
            self.update_tasks_listbox()
    def start_timer(self):
        # Start the timer logic
        self.running = True
        self.start_time = datetime.datetime.now()
        self.update_timer_display()
        # Add any other logic needed to start the timer

        # Update the task label to show the current task
        self.update_task_label()
    def on_closing(self):
        if self.running:
            current_state = {
                'task_name': self.task_name,
                'start_time': self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                'total_seconds': self.total_seconds
            }
            with open('current_state.json', 'w') as file:
                json.dump(current_state, file)
        self.root.destroy()
# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = ProductivityTimerApp(root)

    # Create a frame for the real estate listings
    listings_frame = tk.Toplevel(root)
    listings_frame.title("Real Estate Listings")
    listings_app = RealEstateListingApp(listings_frame)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
