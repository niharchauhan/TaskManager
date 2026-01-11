import os
import time

def send_notification():
    """
    Sends a macOS native notification using osascript, keeping it for 5 seconds.
    """
    # Display the notification
    os.system("""
    osascript -e 'display notification "Your set time has elapsed!" with title "Reminder Alert"'
    """)
    
    # Sleep for 5 seconds to let the notification stay visible
    time.sleep(5)

# Call the function to test
send_notification()
