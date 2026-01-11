import tkinter as tk
from tkinter import Tk
from tkmacosx import Button
from taskbreaker import AgentHead
from tkinter import ttk
from tkinter import simpledialog, messagebox, filedialog
import datetime
import requests
import uuid
import json
import os
import customtkinter as ctk
from tkinter.font import Font
from PIL import Image, ImageTk
import time
from threading import Timer
import pygame
from threading import Thread
import subprocess

users = {
    "nihar": "nihar",
    "ayesha": "ayesha",
    "prakhar": "prakhar",
    "shubham": "shubham",
    "kexuan": "kexuan"
}

class LoginPage:
    def __init__(self, root, on_login):
        self.root = root
        self.root.title("Login Page")
        self.root.geometry("400x300")
        self.root.configure(bg="#F5F5F5")


        ctk.CTkLabel(root, text="Welcome! Please Login", font=("Arial", 16, "bold")).pack(pady=(10, 20))
        
        ctk.CTkLabel(root, text="Username:", font=("Arial", 16)).pack(pady=(5, 5))
        self.username_entry = ctk.CTkEntry(root, font=("Arial", 12), width=200)
        self.username_entry.pack(pady=(0, 10))
        self.username_entry.bind("<Key>", lambda event: self.clear_error())

        ctk.CTkLabel(root, text="Password:", font=("Arial", 16)).pack(pady=5)
        self.password_entry = ctk.CTkEntry(root, show="*", font=("Arial", 12), width=200)
        self.password_entry.pack()
        self.password_entry.bind("<Key>", lambda event: self.clear_error())

        login_button = ctk.CTkButton(root, text="Login", font=("Arial", 16, "bold"), command=self.verify_login)
        login_button.pack(pady=(10, 20))

        self.error_label = ctk.CTkLabel(self.root, text="", font=("Arial", 10, "bold"), text_color="red")

        self.on_login = on_login

    def verify_login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if username in users and users[username] == password:
            messagebox.showinfo("Login Successful", f"Welcome, {username}!", parent=self.root)
            self.on_login(self.root, username)
        else:
            self.display_error("Invalid username or password")

    def display_error(self, message):
        self.error_label.configure(text=message)
        self.error_label.pack(pady=(5, 5))
    
    def clear_error(self):
        if self.error_label.winfo_ismapped():
            self.error_label.pack_forget()

def on_login_success(login_window, username):
    login_window.destroy()
    main_window = tk.Tk()
    app = ProductivityTimerApp(main_window, username)
    main_window.protocol("WM_DELETE_WINDOW", app.on_closing)
    main_window.mainloop()

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

# Productivity Timer Application
class ProductivityTimerApp:
    def __init__(self, root, username):
        self.root = root
        self.root.title("ADHD Task Manager")
        self.username = username
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        self.is_focus_mode = False
        self.reminder_active = False  # Tracks if the reminder is active
        self.beep_thread = None  # Holds the thread for continuous beeping
        self.reminder_timer = None
        self.time_var = tk.StringVar(value="1min")  # Default value
        self.skip_first_beep = False

        # Fallback: Use standard tk.Label
        self.username_label = tk.Label(
            self.top_frame,
            text=f"USER: {self.username}",
            font=("Helvetica", 14, "bold"),  # Bold black text
            fg="#000000",  # Black text
            bg=self.top_frame.cget("bg"),  # Match background of the frame
            anchor="w"
        )
        self.username_label.pack(side=tk.LEFT, padx=10, pady=(10, 5), ipadx=0, ipady=5)




        # self.username_label = tk.Label(self.top_frame, text=f"Logged in as: {self.username}", anchor='e')
        # self.username_label.pack(side=tk.LEFT, padx=10, pady=10)

        self.settings_icon = self.load_icon("setting.png")
        self.logout_icon = self.load_icon("logout.png")
        # Logout button
        self.logout_button = tk.Button(
            self.top_frame,
            image=self.logout_icon,
            command=self.logout,
            bd=1,
            relief=tk.RAISED
        )
        self.logout_button.pack(side=tk.RIGHT, padx=10, pady=10)


        # Add the Settings button here
        # Replace the existing settings button code
        # Settings button
        self.settings_button = tk.Button(
            self.top_frame,
            image=self.settings_icon,
            command=self.open_focus_mode,
            bd=1,
            relief=tk.RAISED
        )
        self.settings_button.pack(side=tk.RIGHT, padx=10, pady=10)
        self.reminder_interval = tk.IntVar(value=5)  # Default to 5 minutes
        self.last_beep_second = -1  # Initialize with a value that ensures the first second will trigger a beep
        self.last_beep_time = datetime.datetime.min  # Initialize with a minimal datetime
        self.local_unsynced_tasks = []  # To store tasks created while offline
        self.is_sound_muted = False
        self.task_breaker = AgentHead(n_breakups=5)
        self.task_name_to_id_map = {}  # Initialize the mapping
        self.command_uuid_to_task_map = {}  # Initialize the command UUID to task mapping
        self.root = root
        self.root.title("ADHD Task Manager")
        self.root.geometry("1000x1000")
        self.root.attributes('-topmost', True)
        self.root.attributes('-alpha',1)
        self.file_path_var = tk.StringVar()
        self.focus_level = "Low"
        self.initialize_variables()
        self.create_widgets()
        self.load_state()
        self.update_timer_display()



    def load_icon(self, path, size=(20, 20)):
        img = Image.open(path)
        img = img.resize(size, Image.LANCZOS)
        return ImageTk.PhotoImage(img)
    
    def open_focus_mode(self):
        """Open a fancy popup window for selecting focus level."""
        # Create the popup window
        focus_popup = ctk.CTkToplevel(self.root)
        focus_popup.title("Select Focus Level")
        focus_popup.geometry("400x300")
        
        focus_popup.transient(self.root)  # Make it modal to the root window
        focus_popup.lift()  # Bring it to the front
        focus_popup.focus_force()

        # Add a label at the top
        ctk.CTkLabel(
            focus_popup,
            text="Choose your Focus Level:",
            font=("Proxima Nova", 20, "bold"),
            text_color="#333333"
        ).pack(pady=20)

        # Variable to store the selected focus level
        focus_level = ctk.StringVar(value=self.focus_level)  # Bind to current focus level

        # Add fancy radio buttons for focus levels
        ctk.CTkRadioButton(
            focus_popup,
            text="Low",
            variable=focus_level,
            value="Low",
            radiobutton_width=20,
            radiobutton_height=20,
            border_width_unchecked=2,
            border_width_checked=4,
            corner_radius=10,
            hover_color="#007BFF",
            fg_color="#007BFF",
            font=("Arial", 14)
        ).pack(anchor="w", padx=40, pady=10)

        ctk.CTkRadioButton(
            focus_popup,
            text="Medium",
            variable=focus_level,
            value="Medium",
            radiobutton_width=20,
            radiobutton_height=20,
            border_width_unchecked=2,
            border_width_checked=4,
            corner_radius=10,
            hover_color="#FFA500",
            fg_color="#FFA500",
            font=("Arial", 14)
        ).pack(anchor="w", padx=40, pady=10)

        ctk.CTkRadioButton(
            focus_popup,
            text="High",
            variable=focus_level,
            value="High",
            radiobutton_width=20,
            radiobutton_height=20,
            border_width_unchecked=2,
            border_width_checked=4,
            corner_radius=10,
            hover_color="#FF5733",
            fg_color="#FF5733",
            font=("Arial", 14)
        ).pack(anchor="w", padx=40, pady=10)

        # Function to save the selected focus level
        def save_focus_level():
            self.focus_level = focus_level.get()
            self.focus_level_label.configure(text=f"Focus Level: {self.focus_level}")
            messagebox.showinfo("Focus Level Set", f"Focus Level set to: {self.focus_level}", parent=self.root)
            focus_popup.destroy()

        # Add Save and Cancel buttons in a horizontal frame
        button_frame = ctk.CTkFrame(focus_popup, fg_color="transparent")
        button_frame.pack(pady=20)

        save_button = ctk.CTkButton(
            button_frame,
            text="Save",
            command=save_focus_level,
            fg_color="#28A745",  # Green color for Save button
            hover_color="#218838",  # Darker green on hover
            text_color="white",
            font=("Arial", 14),
            width=120,
        )
        save_button.grid(row=0, column=0, padx=10)

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=focus_popup.destroy,
            fg_color="#DC3545",  # Red color for Cancel button
            hover_color="#C82333",  # Darker red on hover
            text_color="white",
            font=("Arial", 14),
            width=120,
        )
        cancel_button.grid(row=0, column=1, padx=10)


    def break_down_task(self):
        # Use the current active task for breakdown
        if self.task_name:
            sub_tasks = self.degenerate_task(self.task_name, self.focus_level)
            self.show_sub_tasks(sub_tasks)
        else:
            messagebox.showinfo("No Active Task", "Please select a task to break down.", parent=self.root)
            
    def degenerate_task(self, task_name, focus_level):
        """_summary_

        Args:
            task_name (str): pass the task name to be broken down, in our case it is the active task.
            focus_level (str): pass the focus level to be used for breaking down the task. "low", "medium", "high"

        Returns:
            str: list of sub-tasks(string) generated by the agent.
        """        
        
        subtasks = self.task_breaker.breakup_task(task_name, focus_level)
        return subtasks
    
    def show_sub_tasks(self, sub_tasks):
        if isinstance(sub_tasks, str):
            sub_tasks = sub_tasks.splitlines()

        # Create a new Toplevel window for sub-tasks
        sub_task_window = ctk.CTkToplevel(self.root)
        sub_task_window.title("Sub-tasks")
        sub_task_window.geometry("600x500")

        # Ensure the sub-task window stays in front of the main screen
        sub_task_window.transient(self.root)  # Make it modal to the root window
        sub_task_window.lift()  # Bring it to the front
        sub_task_window.focus_force()  # Set focus on this window

        # Create a frame to center content
        centered_frame = ctk.CTkFrame(sub_task_window, fg_color="transparent")
        centered_frame.pack(expand=True, fill="both", padx=20, pady=20)

        # Add fancy checkboxes for each sub-task
        task_vars = []
        for task in sub_tasks:
            task_var = tk.BooleanVar(value=False)
            task_vars.append(task_var)

            # Use CustomTkinter's CTkCheckBox for fancy checkboxes
            checkbox = ctk.CTkCheckBox(
                centered_frame,
                text=task,
                variable=task_var,
                font=("Arial", 14),
                border_width=2,
                hover_color="#007BFF",  # Hover effect color
                corner_radius=5,  # Rounded corners for a modern look
                command=lambda: self.check_completion(task_vars, sub_task_window),
            )
            checkbox.pack(anchor="w", pady=5)

        # Add a Close button at the bottom
        close_button = ctk.CTkButton(
            sub_task_window,
            text="Close",
            command=sub_task_window.destroy,
            fg_color="#FF5733",  # Orange color for the button
            hover_color="#C13E1A",  # Darker orange on hover
            text_color="white",
            font=("Arial", 14),
            width=120,
            height=40,
        )
        close_button.pack(pady=10)

    def check_completion(self, task_vars, sub_task_window):
        if all(var.get() for var in task_vars):
            messagebox.showinfo("All Sub-tasks Completed", "All sub-tasks are checked off!", parent=self.root)
            sub_task_window.destroy()

    def logout(self):
        self.root.destroy()
        login_window = tk.Tk()
        login_app = LoginPage(login_window, on_login=on_login_success)
        login_window.mainloop()

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
            messagebox.showinfo("Info", "Please select a non-active task to move.", parent=self.root)
        
    def get_todoist_task_id(self, task_name):
        """
        Return the Todoist task ID for the given task name.
        This requires maintaining a mapping of task names to IDs.
        """
        return self.task_name_to_id_map.get(task_name)
    
    def fetch_local_tasks(self, username):
        print(f"Fetching tasks for user: {username}")
        if username == "nihar":
            id = 1
        elif username == "ayesha":
            id = 2
        elif username == "prakhar":
            id = 3
        elif username == "shubham":
            id = 4
        else:
            id = 5
        
        # specify the file name based on the user id
        tasks_file = f"tasks_{id}.json"

        # load tasks from the specified file
        try:
            # Load tasks from the local JSON file
            local_tasks = load_json_file(tasks_file, [])

            # update the tasks and mapping
            self.tasks.clear()
            self.task_name_to_id_map.clear()

            for task in local_tasks:
                task_content = task if isinstance(task, str) else task.get('content', '')
                if task_content:
                    # add task to the list and mapping
                    self.tasks.append(task_content)
                    self.task_name_to_id_map[task_content] = task_content  # Assuming task_content is unique

            # Update the tasks in the JSON file and the listbox
            self.update_tasks_listbox()
            self.show_custom_message("Successfully Loaded", "Tasks loaded successfully")


        except Exception as e:
            self.show_custom_message("Failed", f"Failed to load tasks: {e}.")


    def show_custom_message(self, title, message):
        # Create a dialog window
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)  # Make it modal
        dialog.lift()
        dialog.focus_force()

        # Add a title label
        title_label = ctk.CTkLabel(
            dialog,
            text=title,
            font=("Arial", 18, "bold"),
            text_color="#333333"
        )
        title_label.pack(pady=(20, 10))

        # Add the message label
        message_label = ctk.CTkLabel(
            dialog,
            text=message,
            font=("Arial", 14),
            text_color="#555555",
            wraplength=350,  # Wrap text to fit inside the dialog
            justify="center"
        )
        message_label.pack(pady=(10, 20))

        # Create a button frame for alignment
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=20)

        # Add an OK button
        ok_button = ctk.CTkButton(
            button_frame,
            text="OK",
            command=dialog.destroy,
            fg_color="#007BFF",  # Blue button color
            hover_color="#0056b3",  # Darker blue on hover
            text_color="white",
            font=("Arial", 14),
            width=100,
            height=40,
            corner_radius=8
        )
        ok_button.grid(row=0, column=0, padx=10)

    def send_notification(self, message):
        """
        Send a notification using macOS's `osascript`.
        """
        title = "Reminder Alert"
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script])

    def play_loud_beep(self):
        """
        Plays a loud beep sound using an audio file.
        """
        try:
            pygame.mixer.init()
            pygame.mixer.music.load("beep.mp3")  # Replace with your sound file path
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error playing beep sound: {e}")

    def toggle_sound(self):
        self.is_sound_muted = not self.is_sound_muted
        self.mute_button.configure(text="Unmute" if self.is_sound_muted else "Mute")

    def initialize_variables(self):
        self.running = False
        self.start_time = None
        self.task_name = None
        self.task_list_file = "tasks.json"
        self.tasks = load_json_file(self.task_list_file, [])
        self.total_seconds = 0
    
    def toggle_reminder(self):
        if self.reminder_active:
            # Stop the reminder
            self.reminder_active = False
            self.set_reminder_button.configure(text="Set Reminder")
            print("Reminder stopped.")
        else:
            # Start the reminder
            selected_time = self.time_var.get()  # Get the selected time
            time_map = {
                "1min": 60,
                "2min": 120,
                "5min": 300,
                "10min": 600,
                "30min": 1800,
                "1hour": 3600,
                "2hour": 7200,
                "3hour": 10800,
                "5hour": 18000,
            }
            if selected_time in time_map:
                self.reminder_active = True
                self.set_reminder_button.configure(text="Stop Reminder")
                self.reminder_interval = time_map[selected_time]  # Set the reminder interval in seconds
                self.skip_first_beep = True  # Skip the first beep
                print(f"Reminder set for {selected_time}. Beeping will start after this interval.")
                self.beep_repeating()  # Start the beeping loop
    
    def beep_repeating(self):
        """
        Function to handle beeping and notifications at intervals while the reminder is active.
        Beep will play once after the selected interval and repeat this interval.
        """
        if self.reminder_active:  # Check if the reminder is still active
            if self.skip_first_beep:
                # Skip the first beep and reset the flag
                self.skip_first_beep = False
                print("First beep skipped.")
            else:
                self.play_loud_beep()  # Play the loud beep sound
                self.send_notification("Reminder: Your time has elapsed!")  # Send a push notification
                print("Beep! Reminder time elapsed.")
            
            # Schedule the next beep after the selected interval using self.reminder_interval
            self.after_id = self.root.after(self.reminder_interval * 1000, self.beep_repeating)

    def start_beeping(self):
        """
        Start the beeping process after the timer interval has passed.
        """
        if self.reminder_active:
            self.beep_thread = Thread(target=self.play_loud_beep, daemon=True)  # Using Thread correctly
            self.beep_thread.start()
            self.send_notification("Reminder: Your time has elapsed!")  # Send notification when the timer elapses
            self.beep_repeating()  # Start the repeating beeping loop

    def reset_reminder(self):
        self.reminder_active = False
        self.set_reminder_button.configure(text="Set Reminder")

    def create_widgets(self):
        button_width = 20
        button_height = 4
        button_color = '#007BFF'

        # Main frame for organizing the layout
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Timer Label (Enhanced)
        self.timer_label = ctk.CTkLabel(
            self.main_frame,
            text="00:00:00",
            font=("Helvetica", 48, "bold"),
            text_color="#007BFF",  # Blue for focus
            fg_color="#E3F2FD",  # Light blue background
            corner_radius=10,  # Rounded corners
            width=300,  # Fixed width for alignment
            height=60,  # Increased height for better appearance
            justify="center"
        )
        self.timer_label.pack(pady=20)

        self.task_label = ctk.CTkLabel(
            self.main_frame,
            text="Task: None",
            font=("Helvetica", 24, "bold"),
            text_color="#FF5733",  # Orange text for emphasis
            fg_color="#FFF3E0",  # Light orange background
            corner_radius=10,
            width=400,
            height=50,
            justify="center"
        )
        self.task_label.pack(pady=10)

        self.focus_level_label = ctk.CTkLabel(
            self.main_frame,
            text=f"Focus Level: {self.focus_level}",
            font=("Helvetica", 18, "bold"),
            text_color="#388E3C",  # Green for focus level
            fg_color="#E8F5E9",  # Light green background
            corner_radius=10,
            width=350,
            height=40,
            justify="center"
        )
        self.focus_level_label.pack(pady=5)

        # Dropdown for Reminder
        self.reminder_frame = tk.Frame(self.main_frame)
        self.reminder_frame.pack(pady=10)

        self.time_var = tk.StringVar(value="Select Time")  # Default value for dropdown
        self.time_dropdown = ctk.CTkOptionMenu(
            self.reminder_frame,
            variable=self.time_var,
            values=["1min", "2min", "5min", "10min", "30min", "1hour", "2hour", "3hour", "5hour"],
            width=150
        )
        self.time_dropdown.pack(side=tk.LEFT, padx=10)

        self.set_reminder_button = ctk.CTkButton(
            self.reminder_frame,
            text="Set Reminder",
            command=self.toggle_reminder,
            fg_color="#007BFF",
            hover_color="#0056b3",
            text_color="white",
            width=150
        )
        self.set_reminder_button.pack(side=tk.LEFT, padx=10)

        # Frame for left-side buttons and tasks list
        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 10), pady=5)

        # Left-side buttons frame, aligned with the task list
        self.left_buttons_frame = tk.Frame(self.left_frame)
        self.left_buttons_frame.pack(side=tk.TOP, anchor="n")  # Align at the top

        button_pady = 10  # Set padding to space buttons equally

        # Start button
        self.start_button = ctk.CTkButton(
            self.left_buttons_frame, text="Start",
            command=self.start_or_complete_task,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.start_button.pack(side=tk.TOP, pady=button_pady)

        self.break_task_button = ctk.CTkButton(
            self.left_buttons_frame, text="Break Down Task",
            command=self.break_down_task,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.break_task_button.pack(side=tk.TOP, pady=button_pady)

        # Focus Mode button
        self.focus_mode_button = ctk.CTkButton(
            self.left_buttons_frame, text="Focus Mode",
            command=self.toggle_focus_mode,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.focus_mode_button.pack(side=tk.TOP, pady=button_pady)

        self.exit_focus_mode_button = ctk.CTkButton(self.main_frame, text="Exit Focus Mode", command=self.toggle_focus_mode, fg_color=button_color)

        # Add task button
        self.add_task_button = ctk.CTkButton(
            self.left_buttons_frame, text="Add Task", command=lambda: self.add_task(self.username),
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.add_task_button.pack(side=tk.TOP, pady=button_pady)

        # Swap active task button
        self.swap_task_button = ctk.CTkButton(
            self.left_buttons_frame, text="Swap Active Task", command=self.swap_active_task,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.swap_task_button.pack(side=tk.TOP, pady=button_pady)

        # Move Task to Top button
        self.move_task_button = ctk.CTkButton(
            self.left_buttons_frame, text="Move Task to Top", command=self.move_task_to_top,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.move_task_button.pack(side=tk.TOP, pady=button_pady)

        # Pause button
        self.pause_button = ctk.CTkButton(
            self.left_buttons_frame, text="Pause", command=self.toggle_pause, state=tk.DISABLED,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.pause_button.pack(side=tk.TOP, pady=button_pady)

        # Reset Timer button
        self.reset_timer_button = ctk.CTkButton(
            self.left_buttons_frame, text="Reset Timer", command=self.reset_current_task_timer,
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.reset_timer_button.pack(side=tk.TOP, pady=button_pady)

        # Fetch Todoist Tasks button
        self.fetch_tasks_button = ctk.CTkButton(
            self.left_buttons_frame, text="Fetch Todoist Tasks", command=lambda: self.fetch_local_tasks(self.username),
            width=button_width * 10, height=button_height * 10,
            fg_color=button_color
        )
        self.fetch_tasks_button.pack(side=tk.TOP, pady=button_pady)

        # Frame for tasks list, positioned to the right of the buttons, 10px below the labels
        self.tasks_list_frame = tk.Frame(self.main_frame)
        self.tasks_list_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 20), pady=(10, 20))

        # Listbox for tasks
        # Listbox for tasks with improved appearance
        self.tasks_listbox = tk.Listbox(
            self.tasks_list_frame,
            font=("Helvetica", 16),
            bg="#F0F8FF",  # Light blue background
            fg="#000000",  # Black text
            selectbackground="#007BFF",  # Highlighted item background
            selectforeground="#FFFFFF",  # Highlighted item text
            activestyle="none",  # Disable underline styling
            relief=tk.SOLID,  # Solid border
            borderwidth=2,  # Border width for listbox
            highlightthickness=1,  # Thickness for border
            highlightbackground="#A9A9A9"  # Border color
        )
        self.tasks_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Add custom padding and styling
        self.tasks_listbox.insert(tk.END, *[f"  {task}  " for task in self.tasks])  # Indent tasks for better spacing

        # Scrollbar for tasks
        self.scrollbar = tk.Scrollbar(self.tasks_list_frame, orient=tk.VERTICAL, command=self.tasks_listbox.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tasks_listbox.configure(yscrollcommand=self.scrollbar.set)
        # Move Up Button (Enhanced with Padding)
        self.move_up_button = ctk.CTkButton(
            self.root,
            text="↑",
            command=self.move_task_up,
            fg_color="#007BFF",  # Blue button color
            hover_color="#0056b3",  # Darker blue hover effect
            text_color="white",
            width=40,  # Fixed width
            height=40,  # Fixed height
            corner_radius=10  # Rounded corners
        )
        self.move_up_button.pack(side=tk.RIGHT, padx=10, pady=(0, 20))  # 20px padding from the bottom

        # Move Down Button (Enhanced with Padding)
        self.move_down_button = ctk.CTkButton(
            self.root,
            text="↓",
            command=self.move_task_down,
            fg_color="#007BFF",
            hover_color="#0056b3",
            text_color="white",
            width=40,
            height=40,
            corner_radius=10
        )
        self.move_down_button.pack(side=tk.RIGHT, padx=10, pady=(0, 20))  # 20px padding from the bottom

    def toggle_focus_mode(self):
        """Toggle between Focus Mode and normal mode."""
        if not self.is_focus_mode:
            self.start_button.pack_forget()
            self.break_task_button.pack_forget()
            self.add_task_button.pack_forget()
            self.swap_task_button.pack_forget()
            self.move_task_button.pack_forget()
            self.pause_button.pack_forget()
            self.focus_mode_button.pack_forget()
            self.reset_timer_button.pack_forget()
            self.fetch_tasks_button.pack_forget()
            self.tasks_list_frame.pack_forget()
            self.logout_button.pack_forget()
            self.move_up_button.pack_forget()
            self.move_down_button.pack_forget()

            # Adjust window size for focus mode
            window_width = 600
            window_height = 600
            self.root.geometry(f"{window_width}x{window_height}")

            # Create a new frame for the buttons and center it
            self.focus_mode_buttons_frame = tk.Frame(self.main_frame)
            self.focus_mode_buttons_frame.place(relx=0.5, rely=0.6, anchor="center")  # Center the frame

            # Duplicate "Break Down Task" button for focus mode
            self.break_task_focus_button = ctk.CTkButton(
                self.focus_mode_buttons_frame,
                text="Break Down Task",
                command=self.break_down_task,
                fg_color="#007BFF",  # Blue color
                hover_color="#0056b3",  # Darker blue on hover
                text_color="white",
                font=("Arial", 14),
                width=150,
                height=40,
            )
            self.break_task_focus_button.grid(row=0, column=0, padx=10)  # Use grid for horizontal alignment

            # Exit Focus Mode button
            self.exit_focus_mode_button = ctk.CTkButton(
                self.focus_mode_buttons_frame,
                text="Exit Focus Mode",
                command=self.toggle_focus_mode,
                fg_color="#FF5733",  # Orange color
                hover_color="#C13E1A",  # Darker orange on hover
                text_color="white",
                font=("Arial", 14),
                width=150,
                height=40,
            )
            self.exit_focus_mode_button.grid(row=0, column=1, padx=10)  # Align next to "Break Down Task"

            # Update focus mode state
            self.is_focus_mode = True

        else:
            # Exit Focus Mode: Restore all widgets to their initial layout
            if hasattr(self, "focus_mode_buttons_frame"):
                # Destroy the frame containing focus mode buttons to clean up
                self.focus_mode_buttons_frame.destroy()

            # Repack all previously hidden widgets to restore the main screen layout
            self.timer_label.pack(pady=20)
            self.task_label.pack(pady=10)

            # Restore left-side buttons and their padding
            self.left_buttons_frame.pack(pady=(10, 0))

            button_pady = 10
            # Repack individual buttons in left_buttons_frame with their original spacing
            self.start_button.pack(side=tk.TOP, pady=button_pady)
            self.break_task_button.pack(side=tk.TOP, pady=button_pady)
            self.add_task_button.pack(side=tk.TOP, pady=button_pady)
            self.swap_task_button.pack(side=tk.TOP, pady=button_pady)
            self.move_task_button.pack(side=tk.TOP, pady=button_pady)
            self.pause_button.pack(side=tk.TOP, pady=button_pady)
            self.focus_mode_button.pack(side=tk.TOP, pady=button_pady)
            self.reset_timer_button.pack(side=tk.TOP, pady=button_pady)
            self.fetch_tasks_button.pack(side=tk.TOP, pady=button_pady)

            # Repack tasks list frame and logout button with original padding and alignment
            self.tasks_list_frame.pack(fill=tk.BOTH, expand=True, padx=(20, 20), pady=(20, 20))
            self.logout_button.pack(side=tk.RIGHT, padx=10, pady=10)
            
            self.move_up_button.pack(side=tk.RIGHT, padx=5)
            self.move_down_button.pack(side=tk.RIGHT, padx=5)

            # Restore original window size (as it was when the app opened)
            initial_window_width = 1000  # Replace with your app's initial width
            initial_window_height = 1000  # Replace with your app's initial height
            self.root.geometry(f"{initial_window_width}x{initial_window_height}")

            # Update focus mode state
            self.is_focus_mode = False

    def start_or_complete_task(self):
        if not self.running:
            if not self.tasks:
                messagebox.showwarning("No Tasks", "No tasks available to start.", parent=self.root)
                return
            if self.task_name is None:
                self.task_name = self.tasks.pop(0)
            self.start_time = datetime.datetime.now()
            self.running = True
            self.start_button.configure(text="Complete Task")
            self.pause_button.configure(state=tk.NORMAL)
            self.update_task_label()
            self.update_tasks_listbox()
        else:
            self.complete_local_task(self.username)  # Pass the username to complete the task
            
            
    def toggle_sound(self):
        self.is_sound_muted = not self.is_sound_muted
        self.mute_button.configure(text="Unmute" if self.is_sound_muted else "Mute")
    def toggle_pause(self):
        self.running = not self.running
        self.pause_button.configure(text="Resume" if not self.running else "Pause")
        if self.running:
            self.start_time = datetime.datetime.now() - datetime.timedelta(seconds=self.total_seconds)

    def update_timer_display(self):
        if self.running and self.task_name:  # Check if a task is active and the timer is running
            current_time = datetime.datetime.now()
            elapsed_time = current_time - self.start_time
            self.total_seconds = int(elapsed_time.total_seconds())
            self.timer_label.configure(text=str(elapsed_time).split('.')[0])

            if not self.is_sound_muted and (current_time - self.last_beep_time).total_seconds() >= 1:
                try:
                    # winsound.Beep(1000, 100)  # Beep sound
                    self.last_beep_time = current_time  # Update the last beep time
                except RuntimeError:
                    pass  # Ignore if the beep command fails or overlaps

        self.root.after(1000, self.update_timer_display)  # Schedule the next update

    def prompt_stay_on_track(self):
        response = messagebox.askyesno("Stay on Track", "Are you still working on the task?", parent=self.root)
        if not response:
            reason = simpledialog.askstring("Reason", "Why did you not finish the task?")
            self.log_incompletion(reason)
            
            # Ask if the task should be moved to the bottom of the list
            if messagebox.askyesno("Task Requeue", "Do you want to move this task to the bottom of the list?", parent=self.root):
                self.tasks.append(self.task_name)
                self.update_tasks_listbox()
                self.start_or_complete_task()  # Optionally start the next task immediately

    def log_incompletion(self, reason):
        with open("productivity_log.txt", "a") as file:
            file.write(f"Task Incompletion Reason: {reason}\n")
        # def play_beep(self):
        #     try:
        #         winsound.Beep(1000, 100)  # Beep sound for 100 milliseconds
        #     except RuntimeError:
        #         pass  # Ignore if the previous beep is still playing
    
    def add_task(self, username):
        # Determine user ID based on username
        if username == "nihar":
            id = 1
        elif username == "ayesha":
            id = 2
        elif username == "prakhar":
            id = 3
        elif username == "shubham":
            id = 4
        else:
            id = 5

        # Create a centered dialog for adding tasks
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("New Task")
        dialog.geometry("400x300")  # Define a reasonable size

        # Ensure the dialog stays in front of the main screen
        dialog.transient(self.root)  # Make it a child of the main window
        dialog.lift()                # Bring it to the front
        dialog.focus_force()         # Force focus on this window

        # Workaround for potential CustomTkinter bug (delayed lift)
        dialog.after(100, lambda: dialog.lift())

        # Header label with custom font and padding
        label = ctk.CTkLabel(
            dialog,
            text="Enter your new task",
            font=("Proxima Nova", 20, "bold"),
        )
        label.pack(pady=(20, 10))  # Adjust padding for better alignment

        # Entry widget for task input
        task_entry = ctk.CTkTextbox(dialog, font=("Proxima Nova", 14), width=300, height=100)
        task_entry.pack(pady=20, padx=20)

        # Function to handle adding the task
        def on_add():
            new_task = task_entry.get("1.0", tk.END).strip()
            if new_task:
                file_name = f"tasks_{id}.json"
                current_tasks = load_json_file(file_name, [])
                current_tasks.append(new_task)
                save_json_to_file(current_tasks, file_name)

                self.tasks.append(new_task)
                self.update_tasks_listbox()
                dialog.destroy()

        # Frame to align buttons horizontally
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=10)

        # Styled Add Task button with a green background
        add_button = ctk.CTkButton(
            button_frame,
            text="Add Task",
            command=on_add,
            fg_color="green",  # Green background (CustomTkinter uses `fg_color`)
            hover_color="darkgreen",  # Hover color for the button
            text_color="white",  # White text color
            font=("Arial", 14),
            width=120,
            height=40,
        )
        add_button.grid(row=0, column=0, padx=10)

        # Cancel button to close the dialog
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=dialog.destroy,
            fg_color="#CCCCCC",  # Light grey background for cancel button
            hover_color="#AAAAAA",  # Slightly darker grey for hover effect
            text_color="black",  # Black text color
            font=("Arial", 14),
            width=120,
            height=40,
        )
        cancel_button.grid(row=0, column=1, padx=10)

        # Allow resizing of the dialog box
        dialog.resizable(True, True)
        
        
    def complete_local_task(self,username):
        """
        current task is completed and should be removed from the local tasks.
        """
        if not self.task_name:
            messagebox.showwarning("No task", "No task is currently active.", parent=self.root)
            return
        
        if username == "nihar":
            id = 1
        elif username == "ayesha":
            id = 2
        elif username == "prakhar":
            id = 3
        elif username == "shubham":
            id = 4
        else:
            id = 5

        # Log the completion
        self.log_task()
        completed_task_name = self.task_name
        self.running = False
        self.start_button.configure(text="Start")
        self.pause_button.configure(state=tk.DISABLED)
        self.timer_label.configure(text="00:00:00")
        self.total_seconds = 0
        self.task_name = None
        # self.show_completion_window()
        self.update_task_label()

        tasks_file = f"tasks_{id}.json"
        # delete the completed task from local tasks
        self.remove_completed_task(completed_task_name,tasks_file)

        # start the next task if available
        if self.tasks:
            self.start_or_complete_task()
            
    def remove_completed_task(self, completed_task_name, tasks_file):
        """
        Remove the completed task from the local tasks.
        """

        # Load current tasks from the JSON file
        current_tasks = load_json_file(tasks_file, [])

        # Remove the completed task from the list
        updated_tasks = [task for task in current_tasks if task != completed_task_name]

        # Save the updated tasks back to the JSON file
        save_json_to_file(updated_tasks, tasks_file)

        # Update the local tasks list and the mapping
        if completed_task_name in self.tasks:
            self.tasks.remove(completed_task_name)
        if completed_task_name in self.task_name_to_id_map:
            del self.task_name_to_id_map[completed_task_name]

        # Update the tasks listbox
        self.update_tasks_listbox()
                
    def log_task(self):
        # Get the file path. If none selected, log 'No file selected'
        selected_file_path = self.file_path_var.get() if self.file_path_var.get() else "No file selected"
        log_msg = f"Username: {self.username}\nTask: {self.task_name}\nStart Time: {self.start_time}\nEnd Time: {datetime.datetime.now()}\nFile Path: {selected_file_path}\n"
        
        with open("productivity_log.txt", "a") as log_file:
            log_file.write(log_msg)

        # Reset file path variable after logging
        self.file_path_var.set("")

    def reset_timer(self):
        # Reset the timer logic
        self.running = False
        self.total_seconds = 0
        self.last_beep_second = -1  # If you are using this for sound control
        self.timer_label.configure(text="00:00:00")
        # Add any other logic needed to reset the timer
    def reset_current_task_timer(self):
        """
        Reset the timer for the current task without completing it.
        """
        if self.running and self.task_name:
            self.running = False  # Stop the current timer
            self.total_seconds = 0  # Reset the elapsed seconds to zero
            self.start_time = None  # Clear the start time
            self.timer_label.configure(text="00:00:00")  # Reset the timer label
            self.pause_button.configure(state=tk.DISABLED)  # Disable the pause button
            self.start_button.configure(text="Start")  # Change the start button text back to "Start"

            # Optional: Display a message indicating the timer has been reset
            messagebox.showinfo("Timer Reset", "The timer has been reset.", parent=self.root)

    def select_file_or_folder(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            self.file_path_var.set(file_path)  # Store the selected file path

    def update_task_label(self):
        self.task_label.configure(text=f"Task: {self.task_name if self.task_name else 'None'}")

    def update_tasks_listbox(self):
        self.tasks_listbox.delete(0, tk.END)
        for task in self.tasks:
            padded_task = f"  {task}  "
            self.tasks_listbox.insert(tk.END, padded_task)
        print("updated task list")

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
            self.start_button.configure(text="Complete Task")
            self.pause_button.configure(state=tk.NORMAL)
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
                messagebox.showinfo("Info", "Please select a task to swap with.", parent=self.root)
        else:
            messagebox.showinfo("Info", "No active task to swap.", parent=self.root)

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
    login_window = ctk.CTk()
    login_app = LoginPage(login_window, on_login=on_login_success)
    login_window.mainloop()
