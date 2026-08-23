# Deployment Notes

## Email Secret Encryption

Gmail App Passwords are encrypted before they are stored in PostgreSQL.

Set this environment variable on the Hostinger Docker project:

```text
EMAIL_ENCRYPTION_KEY=<long random secret>
```

Keep this value outside PostgreSQL and outside Git. If it is changed after email settings are saved, the stored Gmail App Password cannot be decrypted and must be replaced from Admin > Settings > Email.

For local development, the backend falls back to `SECRET_KEY` when `EMAIL_ENCRYPTION_KEY` is not set.
