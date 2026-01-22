# Metrics Dashboard

## Overview

The metrics dashboard tracks user engagement and behavior metrics for the Progress RPG platform. It provides admin-only access to key metrics needed for the pilot scheme funding proposal.

## Features

### Metrics Tracked

#### User Metrics
- Total number of users
- New users per day
- Active users per day

#### Engagement & Behavior Metrics
- Active days per week (per user)
- Number of sessions (per user)
- Number of activities logged (per user)
- Total active minutes (per user)
- Week-to-week retention

### Session Tracking

The system uses a hybrid approach to track user sessions:

1. **Real-time tracking**: Sessions are tracked when users call the `fetch_info` endpoint (when opening/loading the game)
2. **Activity-based inference**: Historical sessions can be calculated from activity completion times

A session timeout of 30 minutes is used - activities more than 30 minutes apart are considered separate sessions.

## Data Models

### DailyEngagementSnapshot
Tracks daily activity metrics per user:
- `player`: Foreign key to Player
- `date`: The date of the snapshot
- `had_activity`: Boolean indicating if user was active
- `session_count`: Number of sessions
- `activities_count`: Number of activities completed
- `minutes_active`: Total minutes of activity

### UserEngagementMetrics
Tracks weekly aggregated metrics per user:
- `player`: Foreign key to Player
- `week_start`: Monday of the week
- `week_end`: Sunday of the week
- `active_days_count`: Number of days with activity
- `total_sessions`: Total sessions in the week
- `activities_logged`: Total activities completed
- `total_active_minutes`: Total minutes active
- `retained_from_previous_week`: Boolean for retention

### GlobalMetrics
Tracks platform-wide daily metrics:
- `date`: The date
- `total_users`: Total non-deleted users
- `active_users_today`: Users with activity today
- `new_users_today`: New user signups today
- `total_sessions_today`: Total sessions platform-wide
- `total_activities_today`: Total activities completed
- `total_minutes_today`: Total minutes logged
- `week_over_week_retention`: Retention rate as percentage

## Usage

### Calculating Metrics

#### Via Management Command

Calculate metrics for the last 7 days:
```bash
python manage.py calculate_metrics --days 7
```

Calculate metrics for a specific date:
```bash
python manage.py calculate_metrics --date 2026-01-22
```

Calculate metrics for the last 30 days:
```bash
python manage.py calculate_metrics --days 30
```

#### Via Celery Tasks

The system includes two Celery tasks that run automatically:

1. **Daily metrics** (`calculate_daily_metrics`): Runs daily at 1 AM
2. **Weekly metrics** (`calculate_weekly_metrics`): Runs on Mondays at 2 AM

### Accessing the Dashboard

1. Log in to the Django admin at `/admin/`
2. Navigate to the Metrics section
3. Click on "Dashboard" or visit `/admin/metrics/dashboard/`

The dashboard displays:
- Overall platform metrics (from the most recent date)
- Current week averages (per user)
- Last 7 days trend

### Viewing Detailed Metrics

From the admin, you can access:
- **Global Metrics**: `/admin/metrics/globalmetrics/`
- **User Engagement Metrics**: `/admin/metrics/userengagementmetrics/`
- **Daily Engagement Snapshots**: `/admin/metrics/dailyengagementsnapshot/`

All metrics are read-only in the admin interface.

## Technical Details

### Session Tracking

When a user loads the game (calls `fetch_info`), the system:
1. Checks the cache for their last activity timestamp
2. If no timestamp exists or it's >30 minutes old, counts as a new session
3. Updates the cache with the current timestamp
4. Increments the session count in today's DailyEngagementSnapshot

### Metrics Calculation

The `MetricsCalculator` service class provides methods for calculating all metrics:

- `calculate_daily_snapshot(player, target_date)`: Calculate daily metrics for a player
- `calculate_weekly_metrics(player, week_start)`: Calculate weekly aggregates
- `calculate_global_metrics(target_date)`: Calculate platform-wide metrics
- `calculate_retention_rate(week_start)`: Calculate week-over-week retention
- `calculate_sessions_from_activities(player, target_date)`: Infer sessions from activity timestamps

### Week Definition

Weeks are defined as Monday to Sunday. The `week_start` field always contains a Monday date.

### Retention Calculation

A user is considered "retained" if they:
1. Had at least one activity in the previous week, AND
2. Had at least one activity in the current week

The retention rate is calculated as:
```
(Users active in both weeks) / (Users active in previous week) * 100
```

## Database Migrations

After implementing this feature, run:
```bash
python manage.py makemigrations metrics
python manage.py migrate
```

## Testing

Run the metrics tests with:
```bash
python manage.py test metrics
```

The test suite covers:
- Session tracking functionality
- Daily snapshot calculations
- Weekly metrics aggregation
- Global metrics calculation
- Retention rate calculation

## Notes

- All timestamps use Django's timezone-aware datetimes
- Cache backend uses the existing Django cache configuration
- All metrics are calculated asynchronously via Celery tasks
- The dashboard is admin-only and requires staff permissions
- Historical metrics can be backfilled using the management command
