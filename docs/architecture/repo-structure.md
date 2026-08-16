# Repo Structure

File-location reference for exploration/search. Structure only — see individual files for behavior. Excludes `__pycache__`, `migrations/`, `.pyc`, `node_modules`, `dist`, and other build artifacts.

## Backend

### `api/`
```
api/
├── admin.py
├── apps.py
├── mailchimp.py
├── models.py
├── serializers.py
├── tests.py
├── urls.py
└── views.py
```

### `character/`
```
character/
├── admin.py
├── apps.py
├── data/
│   └── phrases.json
├── filters.py
├── management/commands/
│   ├── generate_character_days.py
│   └── import_birthdates.py
├── models/
│   ├── __init__.py
│   ├── behaviour.py
│   ├── character.py
│   ├── location.py
│   └── needs.py
├── phrases.py
├── serializers.py
├── services/
│   ├── behaviour_services.py
│   ├── character_services.py
│   ├── lifecycle_services.py
│   └── link_services.py
├── signals.py
├── tasks.py
├── tests/
│   ├── test_behaviour_services.py
│   ├── test_character_location.py
│   ├── test_filters.py
│   ├── test_models.py
│   ├── test_needs.py
│   └── test_phrases.py
├── utils.py
└── views.py
```

### `progression/`
```
progression/
├── admin.py
├── apps.py
├── filters.py
├── mixins.py
├── models.py
├── serializers.py
├── tests/
│   ├── base.py
│   ├── test_activities.py
│   ├── test_models.py
│   ├── test_premium_activity_rewards.py
│   ├── test_task_api.py
│   ├── test_task_models.py
│   ├── test_utils.py
│   └── test_viewsets_no_character.py
├── utils.py
└── views.py
```

### `gameplay/`
```
gameplay/
├── admin.py
├── apps.py
├── consumers.py
├── filters.py
├── models.py
├── routing.py
├── serializers.py
├── services/
│   ├── timer_service.py
│   └── xp_modifiers.py
├── signals.py
├── tasks.py
├── templatetags/
│   └── custom_filters.py
├── tests/
│   ├── test_activity_timer_premium.py
│   ├── test_consumers.py
│   ├── test_disconnect_grace.py
│   ├── test_models.py
│   ├── test_stale_connection_sweep.py
│   └── test_views.py
├── urls.py
├── utils.py
└── views.py
```

### `gameworld/`
```
gameworld/
├── admin.py
├── apps.py
├── management/commands/
│   └── test_sun_phases.py
├── models.py
├── tasks.py
├── urls.py
├── utils.py
└── views.py
```

### `locations/`
```
locations/
├── admin.py
├── apps.py
├── management/commands/
│   ├── assign_workers.py
│   ├── force_commute.py
│   ├── generate_fields.py
│   ├── generate_landarea.py
│   ├── generate_nodes.py
│   ├── generate_paths.py
│   ├── generate_points.py
│   ├── place_characters.py
│   ├── populate_interiors.py
│   ├── seed_village_view.py
│   ├── setup_world.py
│   ├── show_map.py
│   ├── generate_characters.py
│   └── generate_villages.py
├── models.py
├── serializers.py
├── services/
│   ├── movement.py
│   ├── schedule.py
│   └── wander.py
├── tasks.py
├── test_bbox_utils.py
├── test_map_serializers.py
├── test_map_viewport.py
├── test_map_world_bounds.py
├── tests.py
├── utils.py
└── views.py
```

### `events/`
```
events/
├── admin.py
├── apps.py
├── listeners.py
├── models.py
└── views.py
```

### `users/`
```
users/
├── achievements.py
├── adapters.py
├── admin.py
├── apps.py
├── auth_backends.py
├── filters.py
├── fixtures/
│   └── tutorial.json
├── forms.py
├── management/commands/
│   ├── assign_missing_characters.py
│   ├── seed_all.py
│   ├── seed_playwright_user.py
│   ├── seed_superuser.py
│   └── send_test_email.py
├── models.py
├── serializers.py
├── services/
│   ├── login_services.py
│   ├── registration_services.py
│   └── waitlist_service.py
├── signals.py
├── tasks.py
├── tests/
│   ├── factories.py
│   ├── test_management_commands.py
│   ├── test_waitlist.py
│   └── tests.py
├── utils.py
├── validators.py
└── views.py
```

### `payments/`
```
payments/
├── admin.py
├── apps.py
├── emails.py
├── forms.py
├── management/commands/
│   ├── end_active_subscription.py
│   ├── provision_free_subscriptions.py
│   └── sync_stripe.py
├── models.py
├── serializers.py
├── services.py
├── signals.py
├── tests.py
├── urls.py
├── utils.py
├── views.py
└── webhooks.py
```

### `server_management/`
```
server_management/
├── admin.py
├── apps.py
├── management/commands/
│   ├── activate_maintenance.py
│   └── pause_timers.py
├── middleware.py
├── models.py
├── scripts/
│   ├── activate_maintenance.py
│   └── deactivate_maintenance.py
├── serializers.py
├── tasks.py
├── tests.py
├── urls.py
└── views.py
```

### `economy/`
```
economy/
├── admin.py
├── apps.py
├── constants.py
├── conversion.py
├── management/commands/
│   ├── economy_dry_run.py
│   ├── economy_forecast.py
│   └── economy_status.py
├── models.py
├── tasks.py
└── tests/
    ├── test_constants.py
    ├── test_conversion.py
    ├── test_field_crop.py
    └── test_tasks.py
```

### `core/`
```
core/
├── admin.py
├── apps.py
├── checks.py
├── models.py
├── tests.py
├── urls.py
└── views.py
```

### `progress_rpg/`
```
progress_rpg/
├── asgi.py
├── celery.py
├── decorators.py
├── exceptions.py
├── middleware/
│   ├── channels_jwt.py
│   ├── logging_context.py
│   └── timezone.py
├── settings/
│   ├── base.py
│   ├── dev.py
│   ├── prod.py
│   ├── settings.py
│   ├── test.py
│   └── utils.py
├── tests/
│   ├── test_channels_jwt_middleware.py
│   └── test_settings_utils.py
├── urls.py
├── wsgi.py
```

## Frontend (`frontend/src/`)

```
src/
├── App.tsx
├── AppContent.tsx
├── main.tsx
├── config.ts
├── featureFlags.ts
├── ds-entry.js
├── vite-env.d.ts
├── api/                    — Axios request functions per resource (activities, tasks, skills, map, player, auth, ...)
├── assets/
├── components/             — one folder per component (Component.tsx, .module.scss, .test.tsx, .stories.tsx)
│   ├── Achievements/
│   ├── ActivitiesPanel/
│   ├── ActivityInput/
│   ├── ActivityTimeline/
│   ├── AlertDialog/
│   ├── BackToTopButton/
│   ├── Button/
│   ├── CategoriesPanel/
│   ├── CharacterCurrentActivity/
│   ├── ComingSoonPanel/
│   ├── CurrentActivity/
│   ├── EntitySearchInput/
│   ├── FeedbackWidget/
│   ├── Form/
│   ├── Input/
│   ├── List/
│   ├── Map/                — Map.tsx, MapTooltips.tsx, utils.ts (MapLibre)
│   ├── Modal/
│   ├── OnlineCountBadge/
│   ├── PlayerItemList/
│   ├── PopulationCentreResidents/
│   ├── ProgressBar/
│   ├── ProjectsPanel/
│   ├── Seo/
│   ├── SkillsPanel/
│   ├── StaticBanner/
│   ├── SupportFlow/         — SupportFlowModal.tsx, supportFlowReducer.ts, screens/
│   ├── TasksPanel/
│   ├── Toast/
│   ├── Tooltip/
│   ├── Turnstile/
│   ├── TutorialModal/
│   ├── UnifiedTimerHome/
│   ├── WaitlistForm/
│   ├── ErrorFallback.tsx
│   ├── FeatureToggle.tsx
│   ├── MaintenanceWatcher.tsx
│   └── PrivateRoute.tsx
├── context/                — AuthContext, GameContext, MaintenanceContext, OnlineCountContext, ToastContext, WebSocketContext
├── hooks/                  — TanStack Query hooks per resource (useActivities, useTasks, useSkills, useMap, usePlayer, ...) plus useWebSocket*, useFeatureFlag
├── layout/
│   ├── ActivityList/
│   ├── Footer/
│   ├── Infobar/            — Infobar.tsx, AchievementBadges.tsx
│   ├── NavDrawer/
│   ├── Navbar/
│   ├── Player/              — PlayerContent.tsx
│   └── _two-columns.scss
├── pages/                  — one folder per route (Page.tsx, .module.scss, .test.tsx)
│   ├── Account/
│   ├── Checkout/            — UpgradePage.tsx
│   ├── EditAccount/
│   ├── ForgotPasswordPage/
│   ├── Game2/                — ActivityTimelinePage.tsx
│   ├── Home/
│   ├── LegalPage/
│   ├── LibraryPage/
│   ├── LoginPage/
│   ├── LogoutPage/
│   ├── MaintenancePage/
│   ├── MapPage/
│   ├── NotFoundPage/
│   ├── PasswordResetConfirmPage/
│   ├── PasswordResetRequestPage/
│   ├── PlayerPage/
│   ├── PrivacyPolicyPage/
│   ├── RegisterPage/
│   ├── SupportPage/
│   ├── TermsOfServicePage/
│   ├── CancelPage.tsx
│   ├── ConfirmationPage.tsx
│   ├── SuccessPage.tsx
│   └── UnavailablePage.tsx
├── routes/                 — AppRoutes.jsx, routePaths.js, routesConfig.jsx
├── styles/
│   ├── base/                — _reset.scss, _global.scss, _a11y.scss, _variables.scss
│   ├── semantic/            — _colors.scss, _spacing.scss, _typography.scss
│   ├── tokens/              — _colors.scss, _spacing.scss, _typography.scss
│   ├── utilities/           — _mixins.scss, _list-pages.scss, _tier-colors.scss
│   ├── _accessibility.scss
│   └── main.scss
├── test/
│   └── setup.js
├── types/                  — api.ts, domain.ts, enums.ts, timers.ts, index.ts
├── utils/                  — analytics, apiErrors, authStorage, formatUtils, playerNameValidation, sounds, userPreferences, ...
└── websockets/
    └── handleGlobalWebSocketEvent.ts
```
