# Phase 7 Spec: User Onboarding and Access Control (No SMTP, Invite Only)

## Intent and constraints
**Target:** Post v1.0, implemented during Phase 7  
**Primary goal:** Allow admin to invite trusted agents while enforcing Canon ownership rules.

**Hard constraints:**
1. Invite only. No self-registration.
2. Admin can manage accounts but never access user-owned client/contact data.
3. No SMTP required initially. Manual copy-and-send invite/reset links.
4. Users can change password inside the app.
5. Locked-out users recover via admin-generated reset link.

## Non-goals
- No guided tours or heavy onboarding UX
- No sample data
- No teams
- No 2FA implementation (planned only)

## Roles and permissions
### Roles
- **Admin:** Invite, disable users, generate reset links. No data access.
- **User:** Full access to own data only.

### Account states
- invited
- active
- disabled

## Canon data ownership
All user-owned tables must be scoped by `current_user.id`.  
Admin screens must never query or display user data or even derived counts.

## Database changes
### users (extensions)
- id
- email
- password_hash
- role
- status
- invited_at
- activated_at
- last_login_at
- onboarding_completed_at
- force_password_reset

### user_invites
- id
- email
- invited_by_user_id
- token_hash
- expires_at
- used_at
- revoked_at
- created_at

### password_resets
- id
- user_id
- created_by_user_id
- token_hash
- expires_at
- used_at
- created_at

## Token rules
- Cryptographically secure
- Stored hashed only
- Single-use
- Time-limited

## Admin UI
Route: /admin/users

Shows:
- email
- role
- status
- invited date
- activated date
- last login

Actions:
- invite user
- copy invite link
- revoke invite
- disable/enable user
- generate password reset link

## User flows
### Accept invite
Route: /accept-invite/<token>  
User sets password → account activated → redirect to dashboard or welcome.

### Change password
Route: /settings/security  
Requires current password.

### Reset password (admin-generated)
Route: /reset-password/<token>

## Admin recovery
Local-only script:
- promote user to admin
- reset admin password
- disable user
- bootstrap first admin

## Deferred
- SMTP email sending
- 2FA
- Teams

## Acceptance criteria
- Admin can manage users without seeing data
- Users own all client data
- Password flows work without email
