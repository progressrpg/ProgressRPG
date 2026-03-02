import sys
from django.conf import settings
import socket, os, subprocess, psycopg2, re

PG_ID_MAX_LENGTH = 63


def is_running_in_docker():
    docker_env = os.environ.get("DOCKER", "").lower()
    if docker_env in ("1", "true", "yes"):
        return True

    if os.path.exists("/.dockerenv"):
        return True

    try:
        with open("/proc/1/cgroup", "r", encoding="utf-8") as cgroup_file:
            cgroup_data = cgroup_file.read()
            if any(
                marker in cgroup_data for marker in ("docker", "containerd", "kubepods")
            ):
                return True
    except OSError:
        pass

    return False


def get_postgres_host():
    in_docker = is_running_in_docker()
    print(f"Running in Docker: {in_docker}", file=sys.stderr)
    selected_host = (
        os.getenv("DB_HOST_DOCKER") if in_docker else os.getenv("DB_HOST_LOCAL")
    )
    if selected_host:
        return selected_host

    return os.getenv("DB_HOST", "db" if in_docker else "localhost")


def rewrite_database_url_host(database_url, host):
    if not database_url:
        return database_url
    return re.sub(r"@[^/:@]+([:/])", rf"@{host}\1", database_url, count=1)


def get_redis_host():
    in_docker = is_running_in_docker()
    selected_host = (
        os.getenv("REDIS_HOST_DOCKER") if in_docker else os.getenv("REDIS_HOST_LOCAL")
    )
    if selected_host:
        return selected_host
    return os.getenv("REDIS_HOST", "redis" if in_docker else "localhost")


def get_redis_url(default_db="0"):
    redis_url = os.getenv("REDIS_URL")
    redis_host = get_redis_host()
    if redis_url:
        return re.sub(r"^(rediss?://)[^/:]+", rf"\1{redis_host}", redis_url, count=1)

    redis_scheme = os.getenv("REDIS_SCHEME", "redis")
    redis_port = os.getenv("REDIS_PORT", "6379")
    redis_db = os.getenv("REDIS_DB", default_db)
    return f"{redis_scheme}://{redis_host}:{redis_port}/{redis_db}"


def get_branch_name():
    """Return the current git branch name, safe for DB naming."""
    try:
        raw = (
            subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                stderr=subprocess.DEVNULL,
            )
            .decode("utf-8")
            .strip()
        )
    except Exception:
        return "default"

    safe = re.sub(r"[^0-9a-zA-Z_]+", "_", raw)

    safe = re.sub(r"_+", "_", safe)

    safe = safe.strip("_")

    if not safe:
        safe = "default"

    safe = safe[:PG_ID_MAX_LENGTH]

    return safe


def get_branch_db_name(base_name=None):
    """Return database name with current branch suffix."""
    branch = get_branch_name()
    base_name = base_name or os.getenv("DB_NAME", "progress_rpg")
    return f"{base_name}_{branch}"


def db_exists(db_name=None):
    """
    Check if a PostgreSQL database already exists.

    Returns True if it exists, False otherwise.
    """
    db_name = db_name or get_branch_db_name()
    db_user = os.getenv("DB_USER", "duncan")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = get_postgres_host()
    db_port = os.getenv("DB_PORT", "5432")

    try:
        conn = psycopg2.connect(
            dbname="postgres",  # Connect to the default DB to query metadata
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
            return cur.fetchone() is not None
    except psycopg2.Error as e:
        print(f"⚠️ Could not connect to Postgres to check DB: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def ensure_branch_db_exists():
    """Ensure a PostgreSQL database exists for the current branch, creating it if necessary."""
    db_name = get_branch_db_name()
    if db_exists(db_name):
        print(f"✅ Database already exists: {db_name}", file=sys.stderr)
        return False

    db_user = os.getenv("DB_USER", "duncan")
    db_password = os.getenv("DB_PASSWORD", "")
    db_host = get_postgres_host()
    db_port = os.getenv("DB_PORT", "5432")

    print(f"⚙️ Creating database for branch: {db_name}")

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE {db_name};")
        print(f"✅ Created database: {db_name}")
        return True
    except psycopg2.Error as e:
        print(f"❌ Failed to create database {db_name}: {e}")
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def migrate_and_seed(branch_db_name):
    """
    Run Django migrations and load seed data for the given branch database.
    Only runs if the database was just created.
    """
    print(f"🚀 Running migrations for {branch_db_name}...")
    try:
        subprocess.run(["python", "manage.py", "migrate"], check=True)
        print("✅ Migrations applied successfully.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        return

    # Load seed data if it exists
    seed_file = os.path.join(os.getcwd(), "seed_data.json")
    if os.path.exists(seed_file):
        print("🌱 Loading seed data...")
        try:
            subprocess.run(
                ["python", "manage.py", "loaddata", "seed_data.json"], check=True
            )
            print("✅ Seed data loaded successfully.")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Failed to load seed data: {e}")
    else:
        print("ℹ️ No seed_data.json file found — skipping.")


def is_vite_running(host="localhost", port=5173) -> bool:
    """Check if Vite dev server is up."""
    try:
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def get_build_number():
    """
    Read BUILD_NUMBER from repo, fallback to environment var or 0.
    """
    try:
        base = getattr(settings, "BASE_DIR", os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(base, "BUILD_NUMBER")
        with open(path, "r") as fh:
            return int(fh.read().strip())
    except Exception:
        return 0
