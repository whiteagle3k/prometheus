"""User profile storage and management system."""

import json
import re
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..processing.extractors import UserDataExtractor, UserDataPoint


class UserProfileStore:
    """Manages persistent storage of user profile data."""
    
    def __init__(self, storage_dir: str = "storage/user_profiles"):
        """Initialize the user profile store."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.extractor = UserDataExtractor()
        self._lock = asyncio.Lock()
    
    def _get_profile_path(self, user_name: str) -> Path:
        """Get the file path for a user's profile."""
        safe_name = "".join(c for c in user_name if c.isalnum() or c in "-_").lower()
        return self.storage_dir / f"{safe_name}_profile.json"
    
    async def load_user_profile(self, user_name: str) -> Dict[str, Any]:
        """Load user profile from storage."""
        if not user_name:
            return {}
        
        profile_path = self._get_profile_path(user_name)
        
        try:
            if profile_path.exists():
                async with self._lock:
                    with open(profile_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
        except Exception as e:
            print(f"⚠️  Error loading user profile for {user_name}: {e}")
        
        return {}
    
    async def save_user_profile(self, user_name: str, profile: Dict[str, Any]) -> None:
        """Save user profile to storage."""
        if not user_name:
            return
        
        profile_path = self._get_profile_path(user_name)
        profile["last_updated"] = datetime.now().isoformat()
        
        try:
            async with self._lock:
                with open(profile_path, 'w', encoding='utf-8') as f:
                    json.dump(profile, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️  Error saving user profile for {user_name}: {e}")
    
    async def update_user_data(self, user_name: str, user_input: str, context: str = "") -> List[UserDataPoint]:
        """Extract and update user data from input."""
        if not user_name:
            return []
        
        # Extract data points from user input using the modular extractor
        extraction_context = {"source_context": context} if context else None
        data_points = self.extractor.extract(user_input, extraction_context)
        
        if not data_points:
            return []
        
        print(f"📊 Extracted {len(data_points)} user data points")
        
        # Load existing profile
        profile = await self.load_user_profile(user_name)
        
        # Initialize profile structure if needed
        if not profile:
            profile = {
                "physical": {},
                "personal": {},
                "goals": {},
                "preferences": {"likes": [], "dislikes": []},
                "feedback": [],
                "last_updated": datetime.now().isoformat()
            }
        
        # Update profile with new data points
        for dp in data_points:
            if dp.category == "physical":
                # Override previous physical data (measurements can change)
                profile["physical"][dp.key] = {
                    "value": dp.value,
                    "timestamp": dp.timestamp.isoformat(),
                    "confidence": dp.confidence,
                    "source": dp.source_context[:50] + "..."
                }
                print(f"  📏 Updated {dp.key}: {dp.value}")
                
            elif dp.category == "personal":
                # Override personal data
                profile["personal"][dp.key] = {
                    "value": dp.value,
                    "timestamp": dp.timestamp.isoformat(),
                    "confidence": dp.confidence,
                    "source": dp.source_context[:50] + "..."
                }
                print(f"  👤 Updated {dp.key}: {dp.value}")
                
            elif dp.category == "goals":
                # Append goals (users can have multiple goals over time)
                if dp.key not in profile["goals"]:
                    profile["goals"][dp.key] = []
                profile["goals"][dp.key].append({
                    "value": dp.value,
                    "timestamp": dp.timestamp.isoformat(),
                    "confidence": dp.confidence,
                    "source": dp.source_context[:50] + "..."
                })
                print(f"  🎯 Added goal: {dp.value}")
                
            elif dp.category == "preferences":
                # Append preferences (can have multiple likes/dislikes)
                if dp.key in ["likes", "dislikes"]:
                    profile["preferences"][dp.key].append({
                        "value": dp.value,
                        "timestamp": dp.timestamp.isoformat(),
                        "confidence": dp.confidence,
                        "source": dp.source_context[:50] + "..."
                    })
                    print(f"  ❤️ Added {dp.key}: {dp.value}")
                    
            elif dp.category == "feedback":
                # Append feedback for learning
                profile["feedback"].append({
                    "type": dp.key,
                    "value": dp.value,
                    "timestamp": dp.timestamp.isoformat(),
                    "confidence": dp.confidence,
                    "context": dp.source_context
                })
                print(f"  💬 Added feedback: {dp.value}")
        
        # Save updated profile
        await self.save_user_profile(user_name, profile)
        
        return data_points
    
    async def get_user_data_context(self, user_name: str) -> str:
        """Get formatted user data for LLM context."""
        if not user_name:
            return ""
        
        profile = await self.load_user_profile(user_name)
        return self._format_user_data_for_context(profile)
    
    def _format_user_data_for_context(self, profile: Dict[str, Any]) -> str:
        """Format user profile data for LLM context."""
        if not profile:
            return ""
        
        context_parts = ["=== USER PROFILE DATA ==="]
        
        # Physical data
        if profile.get("physical"):
            context_parts.append("Physical Information:")
            for key, data in profile["physical"].items():
                context_parts.append(f"  • {key.replace('_', ' ').title()}: {data['value']}")
        
        # Personal data
        if profile.get("personal"):
            context_parts.append("Personal Information:")
            for key, data in profile["personal"].items():
                context_parts.append(f"  • {key.replace('_', ' ').title()}: {data['value']}")
        
        # Goals
        if profile.get("goals"):
            context_parts.append("Goals:")
            for key, goals in profile["goals"].items():
                for goal in goals[-2:]:  # Show last 2 goals
                    context_parts.append(f"  • {goal['value']}")
        
        # Preferences
        if profile.get("preferences"):
            prefs = profile["preferences"]
            if prefs.get("likes"):
                context_parts.append("Likes:")
                for like in prefs["likes"][-3:]:  # Show last 3
                    context_parts.append(f"  • {like['value']}")
            if prefs.get("dislikes"):
                context_parts.append("Dislikes:")
                for dislike in prefs["dislikes"][-3:]:  # Show last 3
                    context_parts.append(f"  • {dislike['value']}")
        
        context_parts.append("=== END USER PROFILE ===")
        context_parts.append("")
        
        return "\n".join(context_parts)
    
    async def query_user_data(self, user_name: str, query_type: str = "all") -> Dict[str, Any]:
        """Query specific user data."""
        if not user_name:
            return {}
        
        profile = await self.load_user_profile(user_name)
        
        if query_type == "physical":
            return profile.get("physical", {})
        elif query_type == "personal":
            return profile.get("personal", {})
        elif query_type == "goals":
            return profile.get("goals", {})
        elif query_type == "preferences":
            return profile.get("preferences", {})
        elif query_type == "feedback":
            return profile.get("feedback", [])
        else:
            return profile
    
    async def get_user_data_summary(self, user_name: str) -> str:
        """Get a human-readable summary of user data."""
        if not user_name:
            return "No user identified."
        
        profile = await self.load_user_profile(user_name)
        
        if not profile:
            return f"No profile data available for {user_name}."
        
        summary_parts = [f"Profile for {user_name}:"]
        
        # Physical data
        physical = profile.get("physical", {})
        if physical:
            summary_parts.append("\nPhysical Data:")
            for key, data in physical.items():
                formatted_key = key.replace('_', ' ').title()
                summary_parts.append(f"  • {formatted_key}: {data['value']}")
        
        # Personal data
        personal = profile.get("personal", {})
        if personal:
            summary_parts.append("\nPersonal Information:")
            for key, data in personal.items():
                formatted_key = key.replace('_', ' ').title()
                summary_parts.append(f"  • {formatted_key}: {data['value']}")
        
        # Recent goals
        goals = profile.get("goals", {})
        if goals:
            summary_parts.append("\nRecent Goals:")
            for goal_type, goal_list in goals.items():
                if goal_list:
                    latest_goal = goal_list[-1]  # Most recent goal
                    summary_parts.append(f"  • {latest_goal['value']}")
        
        # Preferences
        preferences = profile.get("preferences", {})
        if preferences.get("likes"):
            summary_parts.append("\nLikes:")
            for like in preferences["likes"][-3:]:  # Last 3 likes
                summary_parts.append(f"  • {like['value']}")
        
        if preferences.get("dislikes"):
            summary_parts.append("\nDislikes:")
            for dislike in preferences["dislikes"][-3:]:  # Last 3 dislikes
                summary_parts.append(f"  • {dislike['value']}")
        
        return "\n".join(summary_parts)
    
    async def is_data_query(self, user_input: str) -> bool:
        """Determine if the user is asking for their stored data."""
        return self.extractor.is_data_query(user_input)
    
    async def cleanup_old_data(self, user_name: str, days_old: int = 365) -> int:
        """Clean up old data points while keeping recent ones."""
        if not user_name:
            return 0
        
        profile = await self.load_user_profile(user_name)
        if not profile:
            return 0
        
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
        cleaned_count = 0
        
        # Clean old goals (keep last 5 per type)
        for goal_type, goals in profile.get("goals", {}).items():
            if len(goals) > 5:
                profile["goals"][goal_type] = goals[-5:]
                cleaned_count += len(goals) - 5
        
        # Clean old preferences (keep last 10 per type)
        for pref_type in ["likes", "dislikes"]:
            prefs = profile.get("preferences", {}).get(pref_type, [])
            if len(prefs) > 10:
                profile["preferences"][pref_type] = prefs[-10:]
                cleaned_count += len(prefs) - 10
        
        # Clean old feedback (keep last 20)
        feedback = profile.get("feedback", [])
        if len(feedback) > 20:
            profile["feedback"] = feedback[-20:]
            cleaned_count += len(feedback) - 20
        
        if cleaned_count > 0:
            await self.save_user_profile(user_name, profile)
            print(f"🗑️  Cleaned {cleaned_count} old data points for {user_name}")
        
        return cleaned_count 