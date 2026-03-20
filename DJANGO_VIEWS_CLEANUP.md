# Django Views Cleanup Summary

## Overview
This document summarizes the cleanup of Django template views that are no longer needed since the full transition to React with API endpoints.

## Removed Views

### gameplay/views.py
Removed the following Django template views (non-API):
- `get_csrf_token()` - CSRF token generation view
- `game_view()` - Main game template view
- `fetch_activities()` - Fetch activities endpoint (replaced by API)
- `fetch_quests()` - Fetch quests endpoint (replaced by API)
- `fetch_info()` - Fetch profile/character info (replaced by API)
- `create_activity()` - Create activity endpoint (replaced by API)
- `submit_activity()` - Submit activity endpoint (replaced by API)
- `choose_quest()` - Choose quest endpoint (replaced by API)
- `complete_quest()` - Complete quest endpoint (replaced by API)
- `submit_bug_report()` - Submit bug report endpoint (replaced by API)
- `test_redis_connection()` - Redis test utility function

**Kept:** All API ViewSets (QuestViewSet, ActivityTimerViewSet, QuestTimerViewSet, BaseTimerViewSet)

### users/views.py
Removed the following Django template views (non-API):
- `index_view()` - Homepage view
- `get_client_ip()` - Utility function for IP retrieval
- `LoginView` - Django template-based login view
- `logout_view()` - Logout view
- `RegisterView` - Django template-based registration view
- `registration_disabled_view()` - Registration disabled page
- `create_profile_view()` - Profile creation view
- `link_character_view()` - Character linking view
- `tutorial_view()` - Tutorial page view
- `profile_view()` - Profile display view
- `edit_profile_view()` - Profile editing view
- `download_user_data()` - User data download view
- `delete_account()` - Account deletion view

**Kept:** ProfileViewSet (API)

**Note:** Password reset views were kept as they may still be needed for email-based password reset flows.

### payments/views.py
Removed the following Django template views:
- `create_checkout_session()` - Stripe checkout session creation
- `subscribe_view()` - Subscription page view

**Note:** Payment functionality should be implemented via API endpoints in the future.

### gameworld/views.py
Removed the following Django template views:
- `get_game_statistics()` - Game statistics view

### server_management/views.py
Removed the following Django template views:
- `maintenance_view()` - Maintenance page view

**Kept:** `maintenance_status()` API endpoint

## API Equivalents

All removed views have API equivalents available at `/api/v1/`:

### Authentication & User Management
- Registration: `POST /api/v1/auth/registration/`
- Login (JWT): `POST /api/v1/auth/jwt/create/`
- Token refresh: `POST /api/v1/auth/jwt/refresh/`
- Email confirmation: `GET /api/v1/auth/confirm_email/<key>/`
- Profile: `GET /api/v1/me/profile/` and `PATCH /api/v1/me/profile/`
- Account deletion: `POST /api/v1/delete_account/`
- User data download: `GET /api/v1/download_user_data/`

### Game Data
- Fetch game info: `GET /api/v1/fetch_info/`
- Characters: `/api/v1/character/` (ViewSet)
- Activities: `/api/v1/player-activities/` (ViewSet)
- Quests: `/api/v1/quests/` (ViewSet)
  - Eligible quests: `GET /api/v1/quests/eligible/`
- Activity timer: `/api/v1/activity_timers/` (ViewSet)
  - Start: `POST /api/v1/activity_timers/start/`
  - Pause: `POST /api/v1/activity_timers/pause/`
  - Complete: `POST /api/v1/activity_timers/complete/`
  - Set activity: `POST /api/v1/activity_timers/set_activity/`
- Quest timer: `/api/v1/quest_timers/` (ViewSet)
  - Start: `POST /api/v1/quest_timers/start/`
  - Pause: `POST /api/v1/quest_timers/pause/`
  - Complete: `POST /api/v1/quest_timers/complete/`
  - Change quest: `POST /api/v1/quest_timers/change_quest/`

### Other
- Maintenance status: `GET /api/v1/maintenance_status/`
- Skills: `/api/v1/skills/` (ViewSet)
- Tasks: `/api/v1/tasks/` (ViewSet)
- Categories: `/api/v1/categories/` (ViewSet)

## Views Still Needing API Equivalents

**NONE** - All functionality has been migrated to API endpoints.

## Frontend Changes Needed

The frontend already uses the API endpoints exclusively. All React components make requests to `/api/v1/` endpoints through the `apiFetch` utility function.

## Templates That Can Be Removed

The following template directories contain files that are no longer used:
- `templates/users/` (except password reset templates)
- `templates/gameplay/`
- `templates/payments/`
- `templates/server_management/maintenance.html`

These templates can be safely removed in a future cleanup as they are no longer referenced by any views.

## URL Routes Removed

The following URL patterns have been removed:
- `/game/` (game_view)
- `/login/` (LoginView)
- `/logout/` (logout_view)
- `/register/` (RegisterView)
- `/django-index` (index_view)
- `/profile/` (profile_view)
- `/edit_profile/` (edit_profile_view)
- `/create_profile/` (create_profile_view)
- `/link_character/` (link_character_view)
- `/tutorial/` (tutorial_view)
- `/download_user_data/` (download_user_data)
- `/delete_account` (delete_account)
- `/subscribe/` (subscribe_view)
- `/choose_quest/` (choose_quest)
- `/create_activity/` (create_activity)
- `/submit_activity/` (submit_activity)
- `/complete_quest/` (complete_quest)
- `/fetch_quests/` (fetch_quests)
- `/fetch_activities/` (fetch_activities)
- `/fetch_info/` (fetch_info)
- `/submit_bug_report/` (submit_bug_report)
- `/get_csrf_token/` (get_csrf_token)
- `/game_statistics/` (get_game_statistics)
- `/maintenance/` (maintenance_view)
- `/registration_disabled/` (registration_disabled_view)

## Testing Notes

- All removed views were Django template-based views that served HTML pages
- The React frontend uses `/api/v1/` endpoints exclusively
- API endpoints remain unchanged and functional
- No breaking changes to the API or frontend
