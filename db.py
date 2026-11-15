"""Database and authentication primitives. All child records are family scoped."""
import hashlib, hmac, os, secrets
from datetime import datetime, timedelta
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

def now(): return datetime.utcnow()
url=os.getenv("DATABASE_URL","sqlite:///./jchess.db")
if url.startswith("postgres://"): url="postgresql+psycopg://"+url[11:]
elif url.startswith("postgresql://"): url="postgresql+psycopg://"+url[13:]
engine=create_engine(url,pool_pre_ping=True,connect_args={"check_same_thread":False} if url.startswith("sqlite") else {})
DB=sessionmaker(engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    username:Mapped[str]=mapped_column(String(40),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(80))
    password_hash:Mapped[str]=mapped_column(Text)
    role:Mapped[str]=mapped_column(String(12))
    must_reset:Mapped[bool]=mapped_column(Boolean,default=False)
class Family(Base):
    __tablename__="families"
    parent_id:Mapped[int]=mapped_column(ForeignKey("users.id"),primary_key=True)
    child_id:Mapped[int]=mapped_column(ForeignKey("users.id"),primary_key=True)
class Login(Base):
    __tablename__="logins"
    token_hash:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    expires_at:Mapped[datetime]=mapped_column(DateTime)
class Puzzle(Base):
    __tablename__="puzzles"
    id:Mapped[str]=mapped_column(String(80),primary_key=True)
    title:Mapped[str]=mapped_column(String(150))
    category:Mapped[str]=mapped_column(String(24),index=True)
    theme:Mapped[str]=mapped_column(String(45),index=True)
    rating:Mapped[int]=mapped_column(Integer,default=800)
    fen:Mapped[str]=mapped_column(Text)
    solution:Mapped[str]=mapped_column(Text)
    explanation:Mapped[str]=mapped_column(Text)
    kind:Mapped[str]=mapped_column(String(12),default="move")
    target:Mapped[str]=mapped_column(String(4),default="")
    source:Mapped[str]=mapped_column(String(32),default="built-in")
class Training(Base):
    __tablename__="training"
    id:Mapped[int]=mapped_column(primary_key=True)
    child_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    puzzle_id:Mapped[str|None]=mapped_column(ForeignKey("puzzles.id"),nullable=True)
    mode:Mapped[str]=mapped_column(String(12),default="puzzle")
    fen:Mapped[str]=mapped_column(Text)
    moves:Mapped[str]=mapped_column(Text,default="[]")
    step:Mapped[int]=mapped_column(Integer,default=0)
    errors:Mapped[int]=mapped_column(Integer,default=0)
    solved:Mapped[bool]=mapped_column(Boolean,default=False)
    revealed:Mapped[bool]=mapped_column(Boolean,default=False)
    version:Mapped[int]=mapped_column(Integer,default=1)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=now)
class Attempt(Base):
    __tablename__="attempts"
    id:Mapped[int]=mapped_column(primary_key=True)
    child_id:Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    puzzle_id:Mapped[str]=mapped_column(ForeignKey("puzzles.id"),index=True)
    correct:Mapped[bool]=mapped_column(Boolean)
    errors:Mapped[int]=mapped_column(Integer,default=0)
    at:Mapped[datetime]=mapped_column(DateTime,default=now)
class AIUsage(Base):
    """Per-parent budget counter, stored without keys or prompts."""
    __tablename__="ai_usage"
    parent_id:Mapped[int]=mapped_column(ForeignKey("users.id"),primary_key=True)
    day:Mapped[str]=mapped_column(String(10),default="")
    requests:Mapped[int]=mapped_column(Integer,default=0)
    daily_limit:Mapped[int]=mapped_column(Integer,default=3)

class AIConfig(Base):
    __tablename__="ai_config"
    parent_id:Mapped[int]=mapped_column(ForeignKey("users.id"),primary_key=True)
    enabled:Mapped[bool]=mapped_column(Boolean,default=False)
    key_cipher:Mapped[str]=mapped_column(Text,default="")

def hash_pw(pw):
    salt=secrets.token_bytes(16)
    key=hashlib.pbkdf2_hmac("sha256",pw.encode(),salt,250000)
    return "pbkdf2:250000:"+salt.hex()+":"+key.hex()
def verify_pw(pw,h):
    try:
        kind,n,s,k=h.split(":")
        return kind=="pbkdf2" and hmac.compare_digest(hashlib.pbkdf2_hmac("sha256",pw.encode(),bytes.fromhex(s),int(n)),bytes.fromhex(k))
    except (ValueError,TypeError): return False
def digest(token): return hashlib.sha256(token.encode()).hexdigest()
def is_parent(db,pid,cid): return db.get(Family,(pid,cid)) is not None
def initialize():
    Base.metadata.create_all(engine)
    demo=os.getenv("DEMO_USERS","false").lower()=="true"
    production=bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))
    pw=os.getenv("BOOTSTRAP_ADMIN_PASSWORD","")
    admin_hash=os.getenv("BOOTSTRAP_ADMIN_HASH","")
    child_hash=os.getenv("BOOTSTRAP_CHILD_HASH","")
    child_pw=os.getenv("BOOTSTRAP_CHILD_PASSWORD","")
    for label,value in (("BOOTSTRAP_ADMIN_PASSWORD",pw),("BOOTSTRAP_CHILD_PASSWORD",child_pw)):
        if value and len(value)<12:
            raise RuntimeError(label+" must have at least 12 characters")
    for label,h in (("BOOTSTRAP_ADMIN_HASH",admin_hash),("BOOTSTRAP_CHILD_HASH",child_hash)):
        if h and (not h.startswith("pbkdf2:250000:") or len(h.split(":"))!=4):
            raise RuntimeError(label+" has invalid password hash format")
    if production and demo:
        raise RuntimeError("DEMO_USERS=true cannot run on Render")
    admin=os.getenv("ADMIN_USERNAME","hoang").strip().lower()
    with DB.begin() as db:
        parent=db.scalar(select(User).where(User.username==admin))
        if not parent and (pw or admin_hash or (demo and not production)):
            parent=User(username=admin,name="Hoang",password_hash=admin_hash or hash_pw(pw or "hoang"),role="parent",must_reset=True)
            db.add(parent);db.flush()
        if parent and (child_pw or child_hash or (demo and not production)):
            child=db.scalar(select(User).where(User.username=="justin"))
            if not child:
                child=User(username="justin",name="Justin",password_hash=child_hash or hash_pw(child_pw or "justin"),role="child",must_reset=True)
                db.add(child);db.flush()
            if not is_parent(db,parent.id,child.id):
                db.add(Family(parent_id=parent.id,child_id=child.id))
