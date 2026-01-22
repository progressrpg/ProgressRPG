# metrics/utils.py

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger("general")

SESSION_TIMEOUT = 1800  # 30 minutes in seconds
CACHE_TIMEOUT = 3600  # 1 hour in seconds


def track_user_session(player):
    """
    Track user sessions using Django cache.
    
    Consider a new session if >30 minutes (1800 seconds) have passed 
    since last activity.
    
    Args:
        player: The Player object
    
    Returns:
        bool: True if a new session was started, False otherwise
    """
    from .models import DailyEngagementSnapshot
    
    cache_key = f"last_activity_{player.id}"
    now = timezone.now()
    today = now.date()
    
    # Get last activity timestamp from cache
    last_activity = cache.get(cache_key)
    
    # Initialize new_session flag
    new_session = False
    
    # Check if this is a new session
    if last_activity is None:
        # First activity or cache expired - count as new session
        new_session = True
    else:
        # Calculate time since last activity
        time_since_last = (now - last_activity).total_seconds()
        if time_since_last > SESSION_TIMEOUT:
            # More than 30 minutes - count as new session
            new_session = True
    
    # Update cache with current timestamp
    cache.set(cache_key, now, CACHE_TIMEOUT)
    
    # If new session, increment session count in today's snapshot
    if new_session:
        snapshot, created = DailyEngagementSnapshot.objects.get_or_create(
            player=player,
            date=today,
            defaults={
                'had_activity': False,
                'session_count': 0,
                'activities_count': 0,
                'minutes_active': 0,
            }
        )
        snapshot.session_count += 1
        snapshot.save(update_fields=['session_count'])
        
        logger.info(f"New session tracked for player {player.id} on {today}")
    
    return new_session
