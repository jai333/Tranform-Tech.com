"""
Smart Job-Candidate Matching Engine
Calculates compatibility scores between candidates and jobs
"""

from typing import Dict, List, Tuple
import json
from datetime import datetime


class MatchingEngine:
    """Calculates job-candidate compatibility scores"""
    
    def __init__(self):
        """Initialize matching weights"""
        self.weights = {
            'skill_match': 0.35,
            'experience_match': 0.25,
            'education_match': 0.15,
            'culture_fit': 0.15,
            'availability': 0.10
        }
    
    def calculate_match(self, candidate_data: Dict, job_data: Dict) -> Dict:
        """
        Calculate overall match score between candidate and job
        
        Args:
            candidate_data: Parsed candidate resume data
            job_data: Job requirements data
        
        Returns:
            Dict containing detailed match scores and analysis
        """
        
        # Calculate component scores
        skill_score = self.calculate_skill_match(
            candidate_data.get('skills', []),
            job_data.get('required_skills', []),
            job_data.get('nice_to_have_skills', [])
        )
        
        experience_score = self.calculate_experience_match(
            candidate_data.get('total_experience_years', 0),
            job_data.get('min_experience_years', 0),
            job_data.get('max_experience_years', 20)
        )
        
        education_score = self.calculate_education_match(
            candidate_data.get('education', []),
            job_data.get('required_education', [])
        )
        
        culture_score = self.calculate_culture_fit(
            candidate_data.get('soft_skills', []),
            job_data.get('required_soft_skills', [])
        )
        
        availability_score = self.calculate_availability(
            candidate_data.get('notice_period', 30),
            job_data.get('urgency', 'normal')
        )
        
        # Calculate weighted total
        total_score = (
            skill_score * self.weights['skill_match'] +
            experience_score * self.weights['experience_match'] +
            education_score * self.weights['education_match'] +
            culture_score * self.weights['culture_fit'] +
            availability_score * self.weights['availability']
        )
        
        return {
            'total_score': round(total_score, 2),
            'match_percentage': round(total_score, 1),
            'scores': {
                'skill_match': round(skill_score, 2),
                'experience_match': round(experience_score, 2),
                'education_match': round(education_score, 2),
                'culture_fit': round(culture_score, 2),
                'availability': round(availability_score, 2),
            },
            'analysis': {
                'matching_skills': self._get_matching_skills(
                    candidate_data.get('skills', []),
                    job_data.get('required_skills', [])
                ),
                'missing_skills': self._get_missing_skills(
                    candidate_data.get('skills', []),
                    job_data.get('required_skills', [])
                ),
                'gap_analysis': self._generate_gap_analysis(
                    candidate_data,
                    job_data,
                    skill_score,
                    experience_score
                ),
                'recommendations': self._generate_recommendations(
                    candidate_data,
                    job_data,
                    total_score
                )
            },
            'calculated_at': datetime.now().isoformat()
        }
    
    def calculate_skill_match(
        self,
        candidate_skills: List[Dict],
        required_skills: List[str],
        nice_to_have_skills: List[str]
    ) -> float:
        """
        Calculate skill match percentage (0-100)
        
        Scoring:
        - Required skill match: Full points
        - Nice-to-have match: Half points
        - Skill level matching: Bonus points
        """
        if not required_skills:
            return 50.0
        
        candidate_skill_names = {s['skill'].lower() for s in candidate_skills}
        required_skills_lower = [s.lower() for s in required_skills]
        nice_to_have_lower = [s.lower() for s in (nice_to_have_skills or [])]
        
        # Calculate matches
        required_matched = sum(
            1 for s in required_skills_lower if s in candidate_skill_names
        )
        nice_to_have_matched = sum(
            1 for s in nice_to_have_lower if s in candidate_skill_names
        )
        
        # Scoring formula
        total_possible = len(required_skills) + (len(nice_to_have_skills or []) * 0.5)
        total_scored = required_matched + (nice_to_have_matched * 0.5)
        
        score = (total_scored / total_possible * 100) if total_possible > 0 else 50
        
        return min(100, score)
    
    def calculate_experience_match(
        self,
        candidate_years: float,
        min_years: int,
        max_years: int
    ) -> float:
        """
        Calculate experience match (0-100)
        
        Scoring:
        - Below minimum: Penalty
        - Between min-max: Full score
        - Above max: Slight penalty (overqualified)
        """
        
        # If within range, full score
        if min_years <= candidate_years <= max_years:
            return 100.0
        
        # Below minimum
        if candidate_years < min_years:
            gap = min_years - candidate_years
            penalty = gap * 10  # 10% penalty per year gap
            return max(0, 100 - penalty)
        
        # Above maximum (overqualified)
        if candidate_years > max_years:
            excess = candidate_years - max_years
            penalty = excess * 5  # 5% penalty per extra year
            return max(75, 100 - penalty)  # Min 75% even if overqualified
        
        return 50.0
    
    def calculate_education_match(
        self,
        candidate_education: List[Dict],
        required_education: List[str]
    ) -> float:
        """Calculate education match (0-100)"""
        
        if not required_education:
            return 50.0
        
        candidate_degrees = {e.get('degree_type', '').lower() for e in candidate_education}
        required_lower = [e.lower() for e in required_education]
        
        # Check for degree matches
        matches = sum(1 for d in required_lower if d in candidate_degrees)
        score = (matches / len(required_education) * 100) if required_education else 50
        
        return min(100, score)
    
    def calculate_culture_fit(
        self,
        candidate_soft_skills: List[Dict],
        required_soft_skills: List[str]
    ) -> float:
        """Calculate culture/soft skill fit (0-100)"""
        
        if not required_soft_skills:
            return 50.0
        
        candidate_skills_names = {s['skill'].lower() for s in candidate_soft_skills}
        required_lower = [s.lower() for s in required_soft_skills]
        
        matches = sum(1 for s in required_lower if s in candidate_skills_names)
        score = (matches / len(required_soft_skills) * 100) if required_soft_skills else 50
        
        return min(100, score)
    
    def calculate_availability(self, notice_period: int, urgency: str) -> float:
        """
        Calculate availability score based on notice period and job urgency
        
        Urgency levels: 'critical' (< 1 week), 'urgent' (< 2 weeks), 
                       'normal' (< 1 month), 'flexible' (> 1 month)
        """
        urgency_mapping = {
            'critical': 7,
            'urgent': 14,
            'normal': 30,
            'flexible': 90
        }
        
        required_availability = urgency_mapping.get(urgency, 30)
        
        if notice_period <= required_availability:
            return 100.0
        
        # Penalty for longer notice period
        gap_days = notice_period - required_availability
        penalty = min(50, gap_days * 2)  # Max 50% penalty
        
        return max(50, 100 - penalty)
    
    def _get_matching_skills(
        self,
        candidate_skills: List[Dict],
        required_skills: List[str]
    ) -> List[str]:
        """Get list of skills that match required skills"""
        candidate_skill_names = {s['skill'].lower(): s['skill'] 
                               for s in candidate_skills}
        
        matching = [
            candidate_skill_names[req.lower()]
            for req in required_skills
            if req.lower() in candidate_skill_names
        ]
        
        return matching
    
    def _get_missing_skills(
        self,
        candidate_skills: List[Dict],
        required_skills: List[str]
    ) -> List[str]:
        """Get list of required skills that candidate is missing"""
        candidate_skill_names = {s['skill'].lower() for s in candidate_skills}
        
        missing = [
            skill for skill in required_skills
            if skill.lower() not in candidate_skill_names
        ]
        
        return missing
    
    def _generate_gap_analysis(
        self,
        candidate_data: Dict,
        job_data: Dict,
        skill_score: float,
        experience_score: float
    ) -> str:
        """Generate human-readable gap analysis"""
        
        gaps = []
        
        # Skill gaps
        if skill_score < 80:
            missing = self._get_missing_skills(
                candidate_data.get('skills', []),
                job_data.get('required_skills', [])
            )
            if missing:
                gaps.append(f"Missing skills: {', '.join(missing[:3])}")
        
        # Experience gaps
        if experience_score < 80:
            req_exp = job_data.get('min_experience_years', 0)
            cand_exp = candidate_data.get('total_experience_years', 0)
            if cand_exp < req_exp:
                gaps.append(
                    f"Experience gap: {req_exp - cand_exp:.1f} years short"
                )
        
        if gaps:
            return "Areas for development: " + "; ".join(gaps)
        
        return "Well-matched candidate with strong fit."
    
    def _generate_recommendations(
        self,
        candidate_data: Dict,
        job_data: Dict,
        total_score: float
    ) -> List[str]:
        """Generate personalized recommendations"""
        
        recommendations = []
        
        if total_score >= 80:
            recommendations.append("Strong candidate - recommend for interview")
        elif total_score >= 60:
            recommendations.append("Moderate fit - consider for interview with discussion")
        else:
            recommendations.append("Consider skill development before interview")
        
        # Missing skills suggestion
        missing = self._get_missing_skills(
            candidate_data.get('skills', []),
            job_data.get('required_skills', [])
        )
        if missing:
            recommendations.append(
                f"Suggest online course for: {missing[0]}"
            )
        
        return recommendations


# Example usage
if __name__ == '__main__':
    engine = MatchingEngine()
    
    # Sample data
    candidate = {
        'skills': [
            {'skill': 'Python', 'category': 'technical', 'proficiency': 'advanced'},
            {'skill': 'Django', 'category': 'technical', 'proficiency': 'intermediate'},
            {'skill': 'SQL', 'category': 'technical', 'proficiency': 'intermediate'},
        ],
        'total_experience_years': 5,
        'education': [{'degree_type': 'Bachelor'}],
        'notice_period': 30
    }
    
    job = {
        'required_skills': ['Python', 'Django', 'PostgreSQL'],
        'nice_to_have_skills': ['Redis', 'Docker'],
        'min_experience_years': 3,
        'max_experience_years': 10,
        'required_education': ['Bachelor'],
        'urgency': 'normal'
    }
    
    match_result = engine.calculate_match(candidate, job)
    print(json.dumps(match_result, indent=2))
