"""
Task definitions for Git Merge Conflict Resolution Environment.

Each task contains:
- conflicted_file: The file content with <<<<<<< / ======= / >>>>>>> markers
- ground_truth: The correctly resolved file
- description: What the task is testing
- conflict_blocks: Parsed conflict data for the environment
"""

from typing import Dict, Any, List


def parse_conflicts(file_content: str) -> List[Dict[str, Any]]:
    """Parse conflict markers from file content into structured blocks."""
    conflicts = []
    lines = file_content.split("\n")
    i = 0
    conflict_idx = 0
    while i < len(lines):
        if lines[i].startswith("<<<<<<<"):
            ours_lines = []
            theirs_lines = []
            i += 1
            # Collect 'ours' side
            while i < len(lines) and not lines[i].startswith("======="):
                ours_lines.append(lines[i])
                i += 1
            i += 1  # skip =======
            # Collect 'theirs' side
            while i < len(lines) and not lines[i].startswith(">>>>>>>"):
                theirs_lines.append(lines[i])
                i += 1
            conflicts.append({
                "index": conflict_idx,
                "ours": "\n".join(ours_lines),
                "theirs": "\n".join(theirs_lines),
                "resolved": False,
            })
            conflict_idx += 1
        i += 1
    return conflicts


# =============================================================================
# TASK 1: EASY — Single conflict in a config file
# Two branches changed the same database config differently
# =============================================================================

EASY_CONFLICTED = '''\
# config.py — Application configuration

APP_NAME = "MergeBot"
VERSION = "2.1.0"

# Database settings
<<<<<<< HEAD
DB_HOST = "prod-db.internal.company.com"
DB_PORT = 5432
DB_NAME = "app_production"
DB_POOL_SIZE = 20
=======
DB_HOST = "prod-db-v2.internal.company.com"
DB_PORT = 5433
DB_NAME = "app_production_v2"
DB_POOL_SIZE = 25
DB_TIMEOUT = 30
>>>>>>> feature/db-migration

# Cache settings
CACHE_TTL = 3600
CACHE_BACKEND = "redis"

# Logging
LOG_LEVEL = "INFO"
'''

EASY_GROUND_TRUTH = '''\
# config.py — Application configuration

APP_NAME = "MergeBot"
VERSION = "2.1.0"

# Database settings
DB_HOST = "prod-db-v2.internal.company.com"
DB_PORT = 5433
DB_NAME = "app_production_v2"
DB_POOL_SIZE = 25
DB_TIMEOUT = 30

# Cache settings
CACHE_TTL = 3600
CACHE_BACKEND = "redis"

# Logging
LOG_LEVEL = "INFO"
'''

EASY_DESCRIPTION = (
    "A Python config file with a single merge conflict. "
    "The 'feature/db-migration' branch upgraded the database connection settings "
    "to point to the new v2 database server with updated port, name, pool size, "
    "and an added timeout parameter. The HEAD branch still has the old settings. "
    "Resolve by accepting the feature branch's newer database migration settings."
)


# =============================================================================
# TASK 2: MEDIUM — Three conflicts in a utility module
# Import conflict + function logic conflict + constant conflict
# =============================================================================

MEDIUM_CONFLICTED = '''\
"""utils.py — Data processing utilities"""

<<<<<<< HEAD
import json
import logging
from datetime import datetime
=======
import json
import logging
import re
from datetime import datetime, timedelta
>>>>>>> feature/enhanced-parsing

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
<<<<<<< HEAD
BATCH_SIZE = 100
TIMEOUT_SECONDS = 30
=======
BATCH_SIZE = 250
TIMEOUT_SECONDS = 60
RETRY_BACKOFF = 2.0
>>>>>>> feature/enhanced-parsing


def parse_record(raw: str) -> dict:
    """Parse a single data record from raw string format."""
<<<<<<< HEAD
    try:
        data = json.loads(raw)
        if "timestamp" in data:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return data
    except json.JSONDecodeError:
        logger.error("Failed to parse record: %s", raw[:50])
        return {}
=======
    try:
        # Strip control characters before parsing
        cleaned = re.sub(r'[\\x00-\\x1f]', '', raw)
        data = json.loads(cleaned)
        if "timestamp" in data:
            ts = datetime.fromisoformat(data["timestamp"])
            data["timestamp"] = ts
            data["age"] = (datetime.now() - ts).total_seconds()
        if "tags" in data and isinstance(data["tags"], str):
            data["tags"] = [t.strip() for t in data["tags"].split(",")]
        return data
    except json.JSONDecodeError:
        logger.warning("Failed to parse record, attempting fallback: %s", raw[:80])
        # Attempt key=value fallback parsing
        result = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
        return result
>>>>>>> feature/enhanced-parsing


def process_batch(records: list) -> list:
    """Process a batch of records."""
    results = []
    for r in records:
        parsed = parse_record(r)
        if parsed:
            results.append(parsed)
    return results
'''

MEDIUM_GROUND_TRUTH = '''\
"""utils.py — Data processing utilities"""

import json
import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BATCH_SIZE = 250
TIMEOUT_SECONDS = 60
RETRY_BACKOFF = 2.0


def parse_record(raw: str) -> dict:
    """Parse a single data record from raw string format."""
    try:
        # Strip control characters before parsing
        cleaned = re.sub(r'[\\x00-\\x1f]', '', raw)
        data = json.loads(cleaned)
        if "timestamp" in data:
            ts = datetime.fromisoformat(data["timestamp"])
            data["timestamp"] = ts
            data["age"] = (datetime.now() - ts).total_seconds()
        if "tags" in data and isinstance(data["tags"], str):
            data["tags"] = [t.strip() for t in data["tags"].split(",")]
        return data
    except json.JSONDecodeError:
        logger.warning("Failed to parse record, attempting fallback: %s", raw[:80])
        # Attempt key=value fallback parsing
        result = {}
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.split("=", 1)
                result[k.strip()] = v.strip()
        return result


def process_batch(records: list) -> list:
    """Process a batch of records."""
    results = []
    for r in records:
        parsed = parse_record(r)
        if parsed:
            results.append(parsed)
    return results
'''

MEDIUM_DESCRIPTION = (
    "A Python utility module with 3 merge conflicts. "
    "Conflict 1: Import statements — the feature branch adds 're' and 'timedelta'. "
    "Conflict 2: Constants — the feature branch increases BATCH_SIZE, TIMEOUT, and adds RETRY_BACKOFF. "
    "Conflict 3: The parse_record function — the feature branch adds control character stripping, "
    "age computation, tag parsing, and a fallback parser for non-JSON input. "
    "All three conflicts should be resolved by accepting the feature branch's enhanced functionality."
)


# =============================================================================
# TASK 3: HARD — Five conflicts with semantic dependencies
# Method renames, new methods calling renamed methods, updated callers
# =============================================================================

HARD_CONFLICTED = '''\
"""user_service.py — User management service"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: int
    username: str
    email: str
<<<<<<< HEAD
    is_active: bool = True
=======
    is_active: bool = True
    role: str = "member"
    last_login: Optional[datetime] = None
>>>>>>> feature/rbac


class UserService:
    """Service for managing users."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id: int = 1

<<<<<<< HEAD
    def add_user(self, username: str, email: str) -> User:
        """Add a new user."""
        user = User(id=self._next_id, username=username, email=email)
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)
=======
    def create_user(self, username: str, email: str, role: str = "member") -> User:
        """Create a new user with a role."""
        user = User(
            id=self._next_id,
            username=username,
            email=email,
            role=role,
            last_login=None,
        )
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def find_user(self, user_id: int) -> Optional[User]:
        """Find user by ID."""
        return self._users.get(user_id)
>>>>>>> feature/rbac

<<<<<<< HEAD
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user."""
        user = self.get_user(user_id)
=======
    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        user = self.find_user(user_id)
>>>>>>> feature/rbac
        if user:
            user.is_active = False
            return True
        return False

<<<<<<< HEAD
    def list_active_users(self) -> List[User]:
        """List all active users."""
        return [u for u in self._users.values() if u.is_active]

    def search_users(self, query: str) -> List[User]:
        """Search users by username or email."""
        query_lower = query.lower()
        return [
            u for u in self._users.values()
            if query_lower in u.username.lower() or query_lower in u.email.lower()
        ]
=======
    def list_active_users(self, role: Optional[str] = None) -> List[User]:
        """List active users, optionally filtered by role."""
        users = [u for u in self._users.values() if u.is_active]
        if role:
            users = [u for u in users if u.role == role]
        return users

    def search_users(self, query: str, role: Optional[str] = None) -> List[User]:
        """Search users by username or email, optionally filtered by role."""
        query_lower = query.lower()
        results = [
            u for u in self._users.values()
            if query_lower in u.username.lower() or query_lower in u.email.lower()
        ]
        if role:
            results = [r for r in results if r.role == role]
        return results

    def update_role(self, user_id: int, new_role: str) -> bool:
        """Update a user's role."""
        user = self.find_user(user_id)
        if user:
            user.role = new_role
            return True
        return False

    def record_login(self, user_id: int) -> bool:
        """Record a user's login timestamp."""
        user = self.find_user(user_id)
        if user:
            user.last_login = datetime.now()
            return True
        return False
>>>>>>> feature/rbac


def create_default_admin(service: UserService) -> User:
    """Create a default admin user."""
<<<<<<< HEAD
    return service.add_user("admin", "admin@example.com")
=======
    return service.create_user("admin", "admin@example.com", role="admin")
>>>>>>> feature/rbac
'''

HARD_GROUND_TRUTH = '''\
"""user_service.py — User management service"""

from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    id: int
    username: str
    email: str
    is_active: bool = True
    role: str = "member"
    last_login: Optional[datetime] = None


class UserService:
    """Service for managing users."""

    def __init__(self):
        self._users: dict[int, User] = {}
        self._next_id: int = 1

    def create_user(self, username: str, email: str, role: str = "member") -> User:
        """Create a new user with a role."""
        user = User(
            id=self._next_id,
            username=username,
            email=email,
            role=role,
            last_login=None,
        )
        self._users[self._next_id] = user
        self._next_id += 1
        return user

    def find_user(self, user_id: int) -> Optional[User]:
        """Find user by ID."""
        return self._users.get(user_id)

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user account."""
        user = self.find_user(user_id)
        if user:
            user.is_active = False
            return True
        return False

    def list_active_users(self, role: Optional[str] = None) -> List[User]:
        """List active users, optionally filtered by role."""
        users = [u for u in self._users.values() if u.is_active]
        if role:
            users = [u for u in users if u.role == role]
        return users

    def search_users(self, query: str, role: Optional[str] = None) -> List[User]:
        """Search users by username or email, optionally filtered by role."""
        query_lower = query.lower()
        results = [
            u for u in self._users.values()
            if query_lower in u.username.lower() or query_lower in u.email.lower()
        ]
        if role:
            results = [r for r in results if r.role == role]
        return results

    def update_role(self, user_id: int, new_role: str) -> bool:
        """Update a user's role."""
        user = self.find_user(user_id)
        if user:
            user.role = new_role
            return True
        return False

    def record_login(self, user_id: int) -> bool:
        """Record a user's login timestamp."""
        user = self.find_user(user_id)
        if user:
            user.last_login = datetime.now()
            return True
        return False


def create_default_admin(service: UserService) -> User:
    """Create a default admin user."""
    return service.create_user("admin", "admin@example.com", role="admin")
'''

HARD_DESCRIPTION = (
    "A Python user service class with 5 merge conflicts involving semantic dependencies. "
    "The 'feature/rbac' branch renamed 'add_user' → 'create_user' and 'get_user' → 'find_user', "
    "added 'role' and 'last_login' fields to the User dataclass, added role-based filtering "
    "to list and search methods, and introduced new methods (update_role, record_login). "
    "Critically, the deactivate_user method and create_default_admin function must call the "
    "renamed methods (find_user, create_user) — resolving one conflict incorrectly will cascade "
    "errors into others. Accept all feature/rbac changes to maintain consistency."
)


# =============================================================================
# TASK REGISTRY
# =============================================================================

TASKS = {
    "easy": {
        "conflicted_file": EASY_CONFLICTED,
        "ground_truth": EASY_GROUND_TRUTH,
        "description": EASY_DESCRIPTION,
        "filename": "config.py",
    },
    "medium": {
        "conflicted_file": MEDIUM_CONFLICTED,
        "ground_truth": MEDIUM_GROUND_TRUTH,
        "description": MEDIUM_DESCRIPTION,
        "filename": "utils.py",
    },
    "hard": {
        "conflicted_file": HARD_CONFLICTED,
        "ground_truth": HARD_GROUND_TRUTH,
        "description": HARD_DESCRIPTION,
        "filename": "user_service.py",
    },
}
