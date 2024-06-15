from sqlalchemy import create_engine, Column, Integer, Boolean, TIMESTAMP, Text, JSON, DateTime, Interval, ForeignKey, Table, String
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from config import config

engine = create_engine(config['SQL_URI'])
Session = sessionmaker(bind=engine)
Base = declarative_base()

log_modules = Table('log_modules', Base.metadata,
    Column('module_id', Integer, ForeignKey('modules.id')),
    Column('log_id', Integer, ForeignKey('logs.id'))
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_name = Column(String(255), nullable=False, unique=True)
    password = Column(Text, nullable=False)
    name = Column(Text)
    rollNo = Column(Text)
    shared_secret = Column(Text)

class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(DateTime)
    user = relationship(User)
    modules = relationship('Module', secondary=log_modules, back_populates='logs')

class Module(Base):
    __tablename__ = 'modules'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    SSID = Column(Text, nullable=False, default="amFOSS_")
    seed = Column(Integer, nullable=False, default=1000)
    seedRefreshInterval = Column(Integer, nullable=False)
    lastRefreshTime = Column(DateTime, nullable=False)
    isPaused = Column(Boolean, nullable=False, default=True)
    logs = relationship('Log', secondary=log_modules, back_populates='modules')


Base.metadata.create_all(engine)