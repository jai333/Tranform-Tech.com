"""
AI/ML functionality views and API endpoints
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
import json
import logging
from pathlib import Path

from tracking_app.models import (
    Candidate, Job, ResumeData, JobMatch, CandidateAISummary, AdvancedSearch
)
from ai.resume_parser import ResumeParser
from ai.scoring_engine import MatchingEngine

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def parse_resume_api(request):
    """
    API endpoint to upload and parse resume
    Accepts: resume file (PDF, DOCX, TXT)
    Returns: JSON with extracted data
    """
    try:
        candidate_id = request.POST.get('candidate_id')
        resume_file = request.FILES.get('resume')
        
        if not candidate_id or not resume_file:
            return JsonResponse({
                'success': False,
                'error': 'Missing candidate_id or resume file'
            }, status=400)
        
        # Get or create candidate
        candidate = get_object_or_404(Candidate, id=candidate_id)
        
        # Save file temporarily
        file_path = default_storage.save(f'temp_resumes/{resume_file.name}', resume_file)
        
        # Parse resume
        parser = ResumeParser()
        try:
            parsed_data = parser.parse_file(default_storage.path(file_path))
            
            # Create or update ResumeData record
            resume_data, created = ResumeData.objects.update_or_create(
                candidate=candidate,
                defaults={
                    'resume_file': resume_file,
                    'email': parsed_data.get('email'),
                    'phone': parsed_data.get('phone'),
                    'linkedin_url': parsed_data.get('linkedin_url'),
                    'skills': parsed_data.get('skills', []),
                    'experience_years': parsed_data.get('experience_years'),
                    'education': parsed_data.get('education', []),
                    'certifications': parsed_data.get('certifications', []),
                    'raw_text': parsed_data.get('raw_text'),
                    'parse_status': 'success',
                }
            )
            
            # Clean up temporary file
            default_storage.delete(file_path)
            
            return JsonResponse({
                'success': True,
                'message': 'Resume parsed successfully',
                'data': {
                    'skills': parsed_data.get('skills', []),
                    'experience_years': parsed_data.get('experience_years'),
                    'education': parsed_data.get('education', []),
                    'certifications': parsed_data.get('certifications', []),
                    'email': parsed_data.get('email'),
                    'phone': parsed_data.get('phone'),
                    'linkedin_url': parsed_data.get('linkedin_url'),
                }
            })
            
        except Exception as e:
            logger.error(f"Resume parsing error: {str(e)}")
            ResumeData.objects.update_or_create(
                candidate=candidate,
                defaults={
                    'parse_status': 'failed',
                    'parse_error': str(e),
                }
            )
            default_storage.delete(file_path)
            
            return JsonResponse({
                'success': False,
                'error': f'Failed to parse resume: {str(e)}'
            }, status=400)
            
    except Exception as e:
        logger.error(f"Resume upload error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def calculate_job_match_api(request):
    """
    API endpoint to calculate job match between candidate and job
    Request: POST with candidate_id and job_id
    Returns: JSON with match scores and analysis
    """
    try:
        data = json.loads(request.body) if request.body else {}
        candidate_id = data.get('candidate_id')
        job_id = data.get('job_id')
        
        if not candidate_id or not job_id:
            return JsonResponse({
                'success': False,
                'error': 'Missing candidate_id or job_id'
            }, status=400)
        
        candidate = get_object_or_404(Candidate, id=candidate_id)
        job = get_object_or_404(Job, id=job_id)
        
        # Check if resume data exists
        try:
            resume_data = candidate.resume_data
        except ResumeData.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Candidate resume not parsed. Please upload and parse resume first.'
            }, status=400)
        
        # Calculate match
        engine = MatchingEngine()
        candidate_profile = {
            'skills': resume_data.skills or [],
            'experience_years': resume_data.experience_years or 0,
            'education': resume_data.education or [],
            'certifications': resume_data.certifications or [],
        }
        
        job_profile = {
            'required_skills': job.get_skills(),
            'experience': job.experience,
            'description': job.description,
        }
        
        match_report = engine.calculate_match(candidate_profile, job_profile)
        
        # Save match to database
        job_match, created = JobMatch.objects.update_or_create(
            candidate=candidate,
            job=job,
            defaults={
                'overall_score': int(match_report['overall_score']),
                'skill_match_score': int(match_report['scores']['skill_match']),
                'experience_match_score': int(match_report['scores']['experience_match']),
                'education_match_score': int(match_report['scores']['education_match']),
                'culture_fit_score': int(match_report['scores']['culture_fit']),
                'availability_score': int(match_report['scores']['availability']),
                'matching_skills': match_report.get('matching_skills', []),
                'missing_skills': match_report.get('missing_skills', []),
                'experience_gap': match_report.get('gap_analysis', ''),
                'recommendations': match_report.get('recommendations', []),
                'is_auto_matched': True,
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Job match calculated successfully',
            'data': {
                'overall_score': match_report['overall_score'],
                'scores': match_report['scores'],
                'matching_skills': match_report.get('matching_skills', []),
                'missing_skills': match_report.get('missing_skills', []),
                'gap_analysis': match_report.get('gap_analysis', ''),
                'recommendations': match_report.get('recommendations', []),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Job match calculation error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_candidate_matches(request, candidate_id):
    """
    Get all job matches for a candidate
    Returns: JSON list of matching jobs with scores
    """
    try:
        candidate = get_object_or_404(Candidate, id=candidate_id)
        
        # Get all job matches with prefetched job data (optimize N+1 queries)
        matches = JobMatch.objects.filter(
            candidate=candidate
        ).select_related('job').order_by('-overall_score')[:20]
        
        match_list = [
            {
                'job_id': match.job.id,
                'job_title': match.job.title,
                'overall_score': match.overall_score,
                'skill_match_score': match.skill_match_score,
                'experience_match_score': match.experience_match_score,
                'education_match_score': match.education_match_score,
                'matching_skills': match.matching_skills,
                'missing_skills': match.missing_skills,
            }
            for match in matches
        ]
        
        return JsonResponse({
            'success': True,
            'candidate_id': candidate_id,
            'matches': match_list,
            'total_matches': len(match_list)
        })
        
    except Exception as e:
        logger.error(f"Get candidate matches error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_job_candidates(request, job_id):
    """
    Get all candidate matches for a job
    Returns: JSON list of candidates with match scores
    """
    try:
        job = get_object_or_404(Job, id=job_id)
        
        # Get all job matches with prefetched candidate data (optimize N+1 queries)
        matches = JobMatch.objects.filter(
            job=job
        ).select_related('candidate').order_by('-overall_score')[:20]
        
        candidate_list = [
            {
                'candidate_id': match.candidate.id,
                'candidate_name': match.candidate.full_name,
                'overall_score': match.overall_score,
                'skill_match_score': match.skill_match_score,
                'experience_match_score': match.experience_match_score,
                'education_match_score': match.education_match_score,
                'matching_skills': match.matching_skills,
                'missing_skills': match.missing_skills,
            }
            for match in matches
        ]
        
        return JsonResponse({
            'success': True,
            'job_id': job_id,
            'candidates': candidate_list,
            'total_candidates': len(candidate_list)
        })
        
    except Exception as e:
        logger.error(f"Get job candidates error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def save_advanced_search(request):
    """
    Save an advanced search configuration
    """
    try:
        data = json.loads(request.body) if request.body else {}
        
        search = AdvancedSearch.objects.create(
            user=request.user,
            name=data.get('name'),
            description=data.get('description', ''),
            skills_filter=data.get('skills_filter', []),
            experience_min=data.get('experience_min'),
            experience_max=data.get('experience_max'),
            location_filter=data.get('location_filter', []),
            salary_min=data.get('salary_min'),
            salary_max=data.get('salary_max'),
            job_type_filter=data.get('job_type_filter', []),
            education_filter=data.get('education_filter', []),
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Search saved successfully',
            'search_id': search.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Save search error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_candidate_ai_summary(request, candidate_id):
    """
    Get AI-generated summary for a candidate
    """
    try:
        candidate = get_object_or_404(Candidate, id=candidate_id)
        
        try:
            summary = candidate.ai_summary
            return JsonResponse({
                'success': True,
                'summary': {
                    'professional_summary': summary.professional_summary,
                    'key_strengths': summary.key_strengths,
                    'development_areas': summary.development_areas,
                    'ideal_roles': summary.ideal_roles,
                    'overall_profile_score': summary.overall_profile_score,
                }
            })
        except CandidateAISummary.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'AI summary not yet generated'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Get AI summary error: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@login_required
def candidate_detail_with_ai(request, candidate_id):
    """
    View candidate profile with AI insights
    """
    from django.db.models import Prefetch
    
    # Get candidate with optimized queries
    candidate = get_object_or_404(Candidate, id=candidate_id)
    
    # Get resume data if exists
    resume_data = None
    try:
        resume_data = candidate.resume_data
    except ResumeData.DoesNotExist:
        pass
    
    # Get AI summary if exists
    ai_summary = None
    try:
        ai_summary = candidate.ai_summary
    except CandidateAISummary.DoesNotExist:
        pass
    
    # Get top job matches
    top_matches = JobMatch.objects.filter(candidate=candidate).select_related('job').order_by('-overall_score')[:5]
    
    context = {
        'candidate': candidate,
        'resume_data': resume_data,
        'ai_summary': ai_summary,
        'top_matches': top_matches,
    }
    
    return render(request, 'tracking_app/candidate_detail_with_ai.html', context)


@login_required
@require_http_methods(["GET"])
def get_jobs_api(request):
    """
    API endpoint to get all available jobs for job matching
    Returns: JSON with job list
    """
    try:
        # Only fetch necessary fields for performance
        jobs = Job.objects.all().only('id', 'title', 'company').values('id', 'title', 'company')
        return JsonResponse({
            'success': True,
            'jobs': list(jobs)
        })
    except Exception as e:
        logger.error(f"Error fetching jobs: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
