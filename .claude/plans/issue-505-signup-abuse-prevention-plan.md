# Plan: Signup Abuse Prevention (#505)

## 1. High-level strategy

Three independent, additive protections layered onto the existing self-serve
registration flow (`CustomRegisterView` / `CustomRegisterSerializer`,
`RegistrationStatusAPIView`), each shippable as its own commit:

1. **IP rate limiting** on `POST /api/v1/auth/registration/`, reusing the
   `django_ratelimit` pattern already applied to `WaitlistSignupAPIView` /
   `WaitlistJoinAPIView`.
2. **Email-verification gating of the cap**: switch the registration-cap
   count (used both in `CustomRegisterSerializer.validate` and
   `RegistrationStatusAPIView.get`) from "all users" to "verified users",
   via one shared helper.
3. **Disposable-email blocklist**: reject known burner domains in
   `CustomRegisterSerializer.validate_email`, using the maintained
   `disposable-email-domains` PyPI package (mirrors the widely-used
   `disposable-email-domains` npm/list project, updated frequently).

CAPTCHA is already implemented (Cloudflare Turnstile, `_verify_turnstile` in
`api/serializers.py`) — out of scope here, not part of this issue's AC.

No new models, endpoints, or services are needed; all three protections plug
into existing files.

---

## 2. Files likely to change

| File | Change | New? |
|---|---|---|
| `api/views.py` | Add `ratelimit` decorator to `CustomRegisterView.create`; change cap check in `RegistrationStatusAPIView.get` to use verified-count helper | existing |
| `api/serializers.py` | Change cap check in `CustomRegisterSerializer.validate` to use verified-count helper; add disposable-domain check in `validate_email` | existing |
| `users/services/registration_services.py` | Add `verified_user_count()` helper (single source of truth for both call sites) | existing |
| `requirements.in` / `requirements.txt` | Add `disposable-email-domains` | existing |
| `users/tests/test_waitlist.py` (or a new `users/tests/test_registration_abuse.py`) | Tests for all three protections | existing / possibly new |

A new test file is only warranted if `test_waitlist.py` is already large/unfocused — see Tests section.

---

## 3. Implementation plan

**Commit 1 — IP rate limiting**
- Add `@method_decorator(ratelimit(key="ip", rate="5/h", method="POST", block=True))` to `CustomRegisterView.create`, matching the existing waitlist views' style.
- Rate chosen tighter than waitlist's `10/h` since account creation is higher-value abuse target; confirm with existing conventions rather than inventing a new scheme.

**Commit 2 — Email verification gating of the cap**
- Add `verified_user_count()` to `users/services/registration_services.py`: `User.objects.filter(is_confirmed=True).count()`.
- Replace `User.objects.count()` in `CustomRegisterSerializer.validate` and `get_user_model().objects.count()` in `RegistrationStatusAPIView.get` with this helper.
- Behavior change: unconfirmed signups no longer consume a cap slot, so registration stays "open" longer and fewer real users get pushed to the waitlist by abandoned/bot signups.

**Commit 3 — Gate admin auto-confirm on registration mode**
- In `CustomUserAdmin.save_model`, only auto-set `is_confirmed = True` for newly-created users when `GameSettings.current().self_serve_registration` is `False`.

**Commit 4 — Disposable email domain blocklist (registration + waitlist)**
- Add `disposable-email-domains` to `requirements.in`, regenerate `requirements.txt` (and `dev-requirements.txt` if it also pins it — check after `pip-compile`).
- Add a shared `reject_disposable_email(value)` validator (likely `users/validators.py`, alongside other field-level validators already there e.g. `clean_player_name`) checking the domain against `disposable_email_domains.blocklist`.
- Wire it into `CustomRegisterSerializer.validate_email`, `WaitlistSignupRequestSerializer`, and `WaitlistJoinRequestSerializer`.

**Commit 5 — Tests**
- Cover all three protections plus the dev/self-serve confirmation fix (see Tests section).

---

## 4. Design decisions

**Rate limit key/scope** — confirmed: `5/h` per IP.
- Chosen: `key="ip"`, matching `WaitlistSignupAPIView`/`WaitlistJoinAPIView` exactly, for consistency.
- Alternative: rate-limit by email instead of/alongside IP — rejected because the issue explicitly asks for IP rate limiting, and email-based limiting is trivially bypassed by an attacker rotating addresses (which is the same attack this endpoint already blocks via the cap/disposable-domain checks).

**Cap-count helper location**
- Chosen: one helper in `users/services/registration_services.py`, used by both `api/serializers.py` and `api/views.py`, instead of duplicating the `EmailAddress` query in each.
- Alternative: inline the query in both places — rejected, it's the same business rule ("what counts toward the cap") and duplicating it risks the two call sites drifting.

**Verified-count definition**
- Chosen: `User.objects.filter(is_confirmed=True).count()`. `is_confirmed` already exists on the `User` model and is kept correctly in sync by `users/signals.py:set_user_confirmed`, which listens for allauth's `email_confirmed` signal — no need to query `EmailAddress` separately.
- Alternative: query `EmailAddress.objects.filter(verified=True)` directly — rejected as redundant; `is_confirmed` is the existing denormalized projection of exactly that state and is already used elsewhere (`UserSerializer`).

**Disposable domain package**
- Chosen: `disposable-email-domains` (PyPI), which mirrors the actively-maintained `disposable-email-domains` community blocklist — satisfies the AC's "maintained package/list, not hand-rolled."
- Alternative: `django-disposable-email-checker` (adds a Django validator/field) — rejected as unnecessary abstraction; we only need a set-membership check in one place, not a reusable Django field type.

**Scope of the disposable-domain check** — confirmed: applies to both registration and waitlist.
- Chosen: a single shared validator (e.g. `users/validators.py::reject_disposable_email(value)`), called from `CustomRegisterSerializer.validate_email` **and** from `WaitlistSignupRequestSerializer`/`WaitlistJoinRequestSerializer`'s `email` field validation.
- Alternative: duplicate the blocklist check inline in each of the three serializers — rejected, same rule in three places invites drift the same way the cap-count logic would.

**Admin-created users auto-confirmed regardless of registration mode**
- Discovered issue: `users/admin.py`'s `CustomUserAdmin.save_model` unconditionally sets `obj.is_confirmed = True` for every new user created via `/admin/` (`if not change: obj.is_confirmed = True`). This is a deliberate concierge-era convenience — staff vouches for the account, no email loop needed — but it is unconditional today, so it stays true even once self-serve registration is live, which is inconsistent with the rest of this issue's "only real confirmation counts" intent.
- Chosen approach: gate that auto-confirm on `GameSettings.current().self_serve_registration` being `False`. While self-serve is off (concierge mode), admin-created users keep being auto-confirmed as today. Once self-serve is on, admin-created users get `is_confirmed=False` like any other signup, unless a staff member deliberately ticks the box in the admin form.
- Alternative: leave admin behavior untouched and only rely on documentation/convention — rejected per explicit user instruction to tie it to the toggle.
- Confirmed with user: `users/admin.py:save_model` is the correct target (not `dev.py`'s `ACCOUNT_EMAIL_VERIFICATION` setting, which was considered and ruled out — the custom registration view bypasses allauth's `complete_signup`, so that global setting doesn't affect `is_confirmed` during self-serve/invite signup at all).

---

## 5. Edge cases

- **Invite-token/invite-code signups**: these bypass the cap check already (existing behavior, unchanged) — verified-count gating only affects the `self_serve_registration` branch's cap comparison.
- **Rate limit + concurrent requests**: `django_ratelimit` with `block=True` returns 403 by default on limit breach; confirm this doesn't collide with the CAPTCHA/turnstile 400 responses in a way that's confusing to the frontend (frontend currently reads `non_field_errors` for the error message — a ratelimit 403 won't have that shape, so `RegisterPage`'s generic fallback message will show, which is acceptable).
- **Verified-count query cost**: `EmailAddress` table is small relative to `User`; a `.distinct().count()` per registration attempt and per `registration_status` poll is fine at current scale, no caching needed.
- **Disposable-domain false positives**: legitimate users on blocked domains get a validation error with no override path — acceptable per AC, but worth a clear error message ("Please use a permanent email address.") rather than a generic one.
- **Package staleness**: pin `disposable-email-domains` without an upper bound cap issue — it's a data-only package released frequently; treat like any other dependency bump going forward (`dev-requirements.txt` note doesn't apply since it's a runtime dep, not a dev one).

---

## 6. Tests

New/updated tests, likely appended to `users/tests/test_waitlist.py` (already covers registration+waitlist interplay) unless it's already unwieldy, in which case split into `users/tests/test_registration_abuse.py`:

- **Rate limiting**: POST to `auth/registration/` beyond the configured rate from the same IP returns 403/429 and does not create a user; requires overriding `RATELIMIT_ENABLE`/cache in test settings the same way existing waitlist rate-limit tests do (check `test_waitlist.py` for the pattern already used there).
- **Cap gating by verification**:
  - Unverified users at/above `registration_cap` do not block new self-serve signups (registration stays open).
  - Verified users at `registration_cap` do block new self-serve signups (existing behavior preserved).
  - `RegistrationStatusAPIView` reflects `registration_open=True`/`False` consistently with the above.
- **Disposable domain blocklist**:
  - Signup with a known disposable domain (e.g. one from the package's list) is rejected with a clear validation error.
  - Signup with a normal domain is unaffected.
  - Same two cases repeated for `WaitlistSignupAPIView` and `WaitlistJoinAPIView`.
- **Admin auto-confirm gating**: creating a user via `CustomUserAdmin` sets `is_confirmed=True` when `self_serve_registration` is off, and `is_confirmed=False` when it's on.

---

## 7. Risks

- Forgetting to update **both** call sites (`serializers.py` cap check and `views.py` status check) consistently — mitigated by extracting the shared helper in Commit 2.
- Picking a rate limit that's too aggressive for legitimate shared-IP scenarios (school/office NAT, mobile carrier CGNAT) — worth confirming the chosen `5/h` figure against any existing product expectations before merging.
- Test flakiness from `django_ratelimit`'s cache backend if the test settings don't isolate/reset the rate-limit cache between tests (same risk already exists for the waitlist tests — reuse whatever fixture/pattern they use).
- Silently changing `RegistrationStatusAPIView` semantics (verified vs. total count) is a behavior change visible to the frontend (`registration_open`) — should be called out in the PR description, not just buried in a diff.

---

## 8. Open questions

All prior open questions were resolved with the user before implementation:
rate limit set at `5/h`/IP, disposable-domain check applies to registration
and both waitlist endpoints, and the admin auto-confirm gating targets
`users/admin.py:CustomUserAdmin.save_model`.
