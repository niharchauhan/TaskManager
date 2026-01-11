from plyer import notification

def send_notification():
    """
    Sends a macOS native notification using plyer.
    """
    notification.notify(
        title="Reminder Alert", 
        message="Your set time has elapsed!",
        timeout=5  # Notification will stay for 5 seconds
    )

# Call the function to test
send_notification()
