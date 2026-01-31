# ntfy

Push notification server.

## User Management

```bash
# Add user
docker exec -it ntfy ntfy user add <username>

# Add admin user
docker exec -it ntfy ntfy user add --role=admin <username>

# Change password
docker exec -it ntfy ntfy user change-pass <username>

# List users
docker exec -it ntfy ntfy user list

# Delete user
docker exec -it ntfy ntfy user del <username>
```

## Topic Access

```bash
# Grant read-write access to topic
docker exec -it ntfy ntfy access <username> <topic> rw

# Grant read-only access
docker exec -it ntfy ntfy access <username> <topic> ro

# Grant write-only access
docker exec -it ntfy ntfy access <username> <topic> wo

# List all access rules
docker exec -it ntfy ntfy access
```

## Test Notification

```bash
# With auth
curl -u username:password -d "Hello" https://your-domain/mytopic

# From CLI
docker exec -it ntfy ntfy publish mytopic "Test message"
```

## Config

- Auth default: `deny-all` (users need explicit topic access)
- Signup: disabled
- Login: enabled
