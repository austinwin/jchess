# Initial family access

The Render Blueprint provisions these two linked users when the database is initialized for the first time.

| Role | Username | Temporary password |
| --- | --- | --- |
| Parent | `hoang` | Provided privately by the deploy operator |
| Child | `justin` | Provided privately by the deploy operator |

Both are required to change passwords before entering the academy. The Render config contains **only salted PBKDF2 password hashes**, never the plaintext passwords. Passwords are not included in this file.

Existing users are not overwritten during restarts. Once first login and password changes have been confirmed, remove the `BOOTSTRAP_ADMIN_HASH` and `BOOTSTRAP_CHILD_HASH` environment variables from Render so that future fresh databases do not reuse temporary account passwords.

Local development still permits `DEMO_USERS=true` with `hoang/hoang` and `justin/justin`. The Render service always disables that switch.

Render free PostgreSQL has limited lifetime. Upgrade or migrate before its expiry; export progress regularly.
