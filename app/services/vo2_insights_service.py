import openai
import os
from typing import Dict, List, Optional
from datetime import datetime
import json

from app.core.logger import get_logger

logger = get_logger("vo2_insights_service")


class VO2InsightsGenerator:
    """Service for generating personalized VO₂max insights using LLM."""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def prepare_insight_context(
        self,
        user_profile: Dict,
        vo2_analysis: Dict,
        trend_analysis: Dict,
        supporting_metrics: Dict,
        comprehensive_score: Dict
    ) -> Dict:
        """Prepare structured context for LLM analysis."""
        
        return {
            "user_profile": {
                "age": user_profile.get('age'),
                "gender": user_profile.get('gender'),
                "email": user_profile.get('email', 'User')
            },
            "current_fitness": {
                "vo2_max": vo2_analysis.get('latest_vo2'),
                "category": vo2_analysis.get('category'),
                "percentile": vo2_analysis.get('percentile'),
                "age_bracket": vo2_analysis.get('age_bracket'),
                "next_level_target": vo2_analysis.get('next_level')
            },
            "trend_analysis": {
                "direction": trend_analysis.get('trend_direction'),
                "improvement_rate_monthly": trend_analysis.get('improvement_rate'),
                "trend_strength": trend_analysis.get('trend_strength'),
                "total_change_percent": trend_analysis.get('total_change_percent'),
                "data_points": trend_analysis.get('data_points')
            },
            "supporting_data": {
                "resting_heart_rate": supporting_metrics.get('resting_heart_rate', {}).get('average'),
                "sleep_score": supporting_metrics.get('sleep_metrics', {}).get('average_score'),
                "sleep_duration": supporting_metrics.get('sleep_metrics', {}).get('average_duration_hours'),
                "daily_steps": supporting_metrics.get('activity_metrics', {}).get('average_daily_steps')
            },
            "comprehensive_assessment": {
                "total_score": comprehensive_score.get('total_score'),
                "grade": comprehensive_score.get('grade'),
                "component_scores": comprehensive_score.get('component_scores', {})
            }
        }
    
    async def generate_insights(self, context: Dict) -> Dict:
        """Generate personalized VO₂max insights using OpenAI."""
        
        try:
            prompt = self._build_insight_prompt(context)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            insights_text = response.choices[0].message.content
            
            # Parse the structured response
            parsed_insights = self._parse_insights_response(insights_text)
            
            return {
                "success": True,
                "insights": parsed_insights,
                "raw_response": insights_text,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {
                "success": False,
                "error": str(e),
                "insights": self._get_fallback_insights(context)
            }
    
    def _build_insight_prompt(self, context: Dict) -> str:
        """Build the specific prompt with user data."""
        
        user = context['user_profile']
        fitness = context['current_fitness']
        trends = context['trend_analysis']
        supporting = context['supporting_data']
        score = context['comprehensive_assessment']
        
        prompt = f"""
Analyze the cardiovascular fitness data for this user:

**User Profile:**
- Age: {user['age'] or 'Not specified'}
- Gender: {user['gender'] or 'Not specified'}

**Current VO₂max Performance:**
- VO₂max: {fitness['vo2_max']} ml/kg/min
- Fitness Category: {fitness['category']}
- Percentile for demographic: {fitness['percentile']}%
- Age bracket: {fitness['age_bracket']}

**Trend Analysis ({trends['data_points']} measurements):**
- Trend direction: {trends['direction']}
- Monthly change rate: {trends['improvement_rate_monthly']} ml/kg/min
- Overall change: {trends['total_change_percent']}%
- Trend reliability: {trends['trend_strength']} (R²)

**Supporting Health Metrics:**
- Resting heart rate: {supporting['resting_heart_rate'] or 'Not available'} bpm
- Sleep quality score: {supporting['sleep_score'] or 'Not available'}/100
- Average sleep duration: {supporting['sleep_duration'] or 'Not available'} hours
- Daily steps: {supporting['daily_steps'] or 'Not available'}

**Comprehensive Fitness Score:**
- Overall score: {score['total_score']}/100 (Grade: {score['grade']})
- Component breakdown: VO₂max: {score['component_scores'].get('vo2_score', 'N/A')}, Trend: {score['component_scores'].get('trend_score', 'N/A')}, Consistency: {score['component_scores'].get('consistency_score', 'N/A')}

**Next Level Target:**
{f"To reach {fitness['next_level_target']['target_level']}: {fitness['next_level_target']['target_vo2']} ml/kg/min (improve by {fitness['next_level_target']['improvement_needed']:.1f})" if fitness.get('next_level_target') else 'Target information not available'}

Please provide comprehensive insights and recommendations based on this data.
"""
        
        return prompt
    
    def _parse_insights_response(self, response_text: str) -> Dict:
        """Parse the LLM response into structured insights."""
        
        sections = {
            'current_assessment': '',
            'trend_analysis': '',
            'key_insights': '',
            'recommendations': '',
            'goals': '',
            'areas_to_monitor': ''
        }
        
        current_section = None
        lines = response_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('## Current Assessment'):
                current_section = 'current_assessment'
                continue
            elif line.startswith('## Trend Analysis'):
                current_section = 'trend_analysis'
                continue
            elif line.startswith('## Key Insights'):
                current_section = 'key_insights'
                continue
            elif line.startswith('## Recommendations'):
                current_section = 'recommendations'
                continue
            elif line.startswith('## Goals'):
                current_section = 'goals'
                continue
            elif line.startswith('## Areas to Monitor'):
                current_section = 'areas_to_monitor'
                continue
            elif line.startswith('##'):
                current_section = None
                continue
            
            if current_section and line:
                sections[current_section] += line + ' '
        
        # Clean up the sections
        for key in sections:
            sections[key] = sections[key].strip()
        
        # If parsing fails, put everything in current_assessment
        if not any(sections.values()):
            sections['current_assessment'] = response_text
        
        return sections
    
    def _get_fallback_insights(self, context: Dict) -> Dict:
        """Provide fallback insights if LLM fails."""
        
        fitness = context['current_fitness']
        trends = context['trend_analysis']
        
        return {
            'current_assessment': f"Your current VO₂max of {fitness['vo2_max']} ml/kg/min places you in the {fitness['category']} category for your demographic.",
            'trend_analysis': f"Based on {trends['data_points']} measurements, your fitness trend is {trends['direction']}.",
            'key_insights': "Continue monitoring your cardiovascular fitness with regular measurements.",
            'recommendations': "Maintain consistent aerobic exercise, track your progress regularly, and consider consulting with a fitness professional.",
            'goals': "Focus on gradual, sustainable improvements in your cardiovascular fitness.",
            'areas_to_monitor': "Keep tracking your VO₂max measurements and supporting health metrics."
        }
    
    def generate_quick_summary(self, context: Dict) -> str:
        """Generate a quick one-sentence summary of fitness status."""
        
        fitness = context['current_fitness']
        trends = context['trend_analysis']
        score = context['comprehensive_assessment']
        
        try:
            trend_text = ""
            if trends['direction'] == 'improving':
                trend_text = f"and improving at {trends['improvement_rate_monthly']:.1f} ml/kg/min per month"
            elif trends['direction'] == 'declining':
                trend_text = f"but declining at {abs(trends['improvement_rate_monthly']):.1f} ml/kg/min per month"
            else:
                trend_text = "with stable performance"
            
            return f"Your VO₂max of {fitness['vo2_max']} ml/kg/min is in the {fitness['category']} range (Grade: {score['grade']}) {trend_text}."
            
        except Exception as e:
            logger.error(f"Error generating quick summary: {e}")
            return f"Your current VO₂max is {fitness.get('vo2_max', 'unknown')} ml/kg/min."
