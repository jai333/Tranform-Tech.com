from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from tracking_app.models import Interview
from uuid import UUID
from django.http import HttpResponseForbidden

# Create your views here.

@login_required
def video_call_room(request, room_uuid):
    # Validate interview and permissions
    interview = get_object_or_404(Interview, meeting_url__icontains=str(room_uuid))

    user = request.user
    # Permission rules expanded:
    # 1. Recruiter who created the interview (FK `user`)
    # 2. Interviewer name match (fallback)
    # 3. Applicant / job-seeker on the related JobSeekerApplication (if interview.applicant relationship present)
    # 4. Email match with Candidate record (commonly used for job-seekers)
    # 5. Admin or staff

    recruiter_user = getattr(interview, 'user', None)

    applicant_user = None
    if hasattr(interview, 'application') and interview.application_id:
        # Interview.application currently points to recruiter-side Application model; however,
        # we may still have JobSeekerApplication via reverse look-up or not set.
        applicant_user = getattr(interview.application, 'applicant', None)

    candidate_email_match = (
        bool(user.email) and
        bool(interview.candidate.email) and
        user.email.lower() == interview.candidate.email.lower()
    )

    allowed = (
        recruiter_user and user == recruiter_user or
        user.username == interview.interviewer or
        (applicant_user and user == applicant_user) or
        candidate_email_match or
        user.is_admin_role or
        user.is_staff
    )

    if not allowed:
        return HttpResponseForbidden("You are not allowed to join this meeting.")

    context = {
        'room_uuid': room_uuid,
        'is_initiator': user.is_recruiter,
        'turn_config': {
            'urls': [
                'stun:stun.l.google.com:19302',  # fallback public STUN
            ]
        }
    }
    return render(request, 'video/room.html', context)
