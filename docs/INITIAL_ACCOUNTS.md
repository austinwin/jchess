# Initial accounts and security

In production, the app provisions **two family-linked accounts once** when both bootstrap passwords are present:

- Parent username: `hoang`; password: `BOOTSTRAP_ADMIN_PASSWORD`
- Child username: `justin`; password: `BOOTSTRAP_CHILD_PASSWORD`

Each password must be at least 12 characters. **Both accounts must change the temporary password at first login**. Public deployment does not allow `hoang/hoang` or `justin/justin`. No credentials are embedded in GitHub or the frontend bundle.

Bootstrap credentials are not re-applied on restarts and will not overwrite a changed password. Once both accounts are verified, you can remove the bootstrap password environment variables from the Render service. The user and family link remain in PostgreSQL.
