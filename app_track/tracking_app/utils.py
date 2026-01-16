import uuid
import secrets
import string

def generate_meeting_id():
    """Generate a unique meeting UUID for internal video calls"""
    return str(uuid.uuid4())

def generate_meeting_url(meeting_id=None):
    """
    Generate an internal meeting URL for the WebRTC video call feature.
    """
    if not meeting_id:
        meeting_id = generate_meeting_id()

    meeting_url = f"/video/video-call/{meeting_id}/"
    return meeting_url, meeting_id 