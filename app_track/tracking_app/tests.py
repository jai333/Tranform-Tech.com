import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from ai.resume_parser import ResumeParser
from tracking_app.models import Candidate, ResumeData


RESUME_TEXT = """John Doe
john.resume@example.com
555-222-3333
linkedin.com/in/john-doe

Experience
Senior Python Developer
Worked on Django and AWS platforms from 2014 to 2024.

Education
Bachelor of Science in Computer Science
"""


class ResumeParserTests(TestCase):
    def test_parse_text_extracts_contact_and_experience_without_optional_nlp(self):
        parsed = ResumeParser().parse_text(RESUME_TEXT)

        self.assertEqual(parsed['contact_info']['email'], 'john.resume@example.com')
        self.assertEqual(parsed['contact_info']['phone'], '555-222-3333')
        self.assertEqual(parsed['contact_info']['linkedin'], 'linkedin.com/in/john-doe')
        self.assertEqual(parsed['total_experience_years'], 1.0)
        self.assertIn('Python', [skill['skill'] for skill in parsed['skills']])
        self.assertIn('Django', [skill['skill'] for skill in parsed['skills']])


class ParseResumeApiTests(TestCase):
    def setUp(self):
        self.temp_media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.temp_media_root)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(shutil.rmtree, self.temp_media_root, True)

        self.user = get_user_model().objects.create_user(
            username='resume-tester',
            email='tester@example.com',
            password='test-pass-123'
        )
        self.client.force_login(self.user)
        self.candidate = Candidate.objects.create(
            first_name='Candidate',
            last_name='One',
            email='candidate.one@example.com',
            user=self.user,
        )

    def test_parse_resume_api_maps_nested_parser_output_into_resume_data(self):
        response = self.client.post(
            reverse('parse-resume-api'),
            {
                'candidate_id': self.candidate.id,
                'resume': SimpleUploadedFile(
                    'resume.txt',
                    RESUME_TEXT.encode('utf-8'),
                    content_type='text/plain',
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()

        self.assertTrue(payload['success'])
        self.assertEqual(payload['data']['email'], 'john.resume@example.com')
        self.assertEqual(payload['data']['phone'], '555-222-3333')
        self.assertEqual(payload['data']['linkedin_url'], 'https://linkedin.com/in/john-doe')
        self.assertEqual(payload['data']['experience_years'], 1.0)

        resume_data = ResumeData.objects.get(candidate=self.candidate)
        self.assertEqual(resume_data.email, 'john.resume@example.com')
        self.assertEqual(resume_data.phone, '555-222-3333')
        self.assertEqual(resume_data.linkedin_url, 'https://linkedin.com/in/john-doe')
        self.assertEqual(resume_data.experience_years, 1.0)
        self.assertEqual(resume_data.parse_status, 'success')
