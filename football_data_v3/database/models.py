import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from config.settings import DB_TYPE, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME

# Set up logging
logger = logging.getLogger(__name__)

# Create the database connection string based on the database type
if DB_TYPE == "postgresql":
    conn_string = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_TYPE == "mysql":
    conn_string = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
elif DB_TYPE == "sqlite":
    conn_string = f"sqlite:///{DB_NAME}.db"
else:
    logger.error(f"Unsupported database type: {DB_TYPE}")
    raise ValueError(f"Unsupported database type: {DB_TYPE}")

# Create engine and session
try:
    engine = create_engine(conn_string)
    Session = sessionmaker(bind=engine)
    Base = declarative_base()
    logger.info(f"Database connection established: {DB_TYPE}")
except Exception as e:
    logger.error(f"Failed to connect to database: {str(e)}")
    raise

class Match(Base):
    """Match model representing a football match"""
    __tablename__ = 'matches'
    
    id = Column(Integer, primary_key=True)
    league_id = Column(Integer, index=True)
    league_name = Column(String(255), nullable=True)
    localteam_id = Column(Integer, index=True)
    localteam_name = Column(String(255), nullable=True)
    visitorteam_id = Column(Integer, index=True)
    visitorteam_name = Column(String(255), nullable=True)
    starting_at_timestamp = Column(DateTime, index=True)
    status = Column(String(50), nullable=True)
    score_localteam = Column(Integer, nullable=True)
    score_visitorteam = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="match", cascade="all, delete-orphan")
    odds = relationship("Odd", back_populates="match", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Match(id={self.id}, {self.localteam_name} vs {self.visitorteam_name})>"

class Prediction(Base):
    """Prediction model for match predictions"""
    __tablename__ = 'predictions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False, index=True)
    prediction_id = Column(Integer, nullable=True)  # Original ID from SportMonks
    type_id = Column(Integer, nullable=True)
    type_name = Column(String(255), nullable=False)
    developer_name = Column(String(100), nullable=False, index=True)
    selection = Column(String(100), nullable=False)
    probability = Column(Float, nullable=False)  # Stored as percentage (e.g., 39.25)
    
    # Extra fields for value bets
    bookmaker = Column(String(100), nullable=True)
    fair_odd = Column(Float, nullable=True)
    odd = Column(Float, nullable=True)
    stake = Column(Float, nullable=True)
    is_value = Column(Boolean, nullable=True)
    
    # JSON representation of the prediction (for advanced queries)
    json_data = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    match = relationship("Match", back_populates="predictions")
    
    # Unique constraint to avoid duplicates
    __table_args__ = (UniqueConstraint('match_id', 'developer_name', 'selection', 
                                      name='unique_prediction'),)
    
    def __repr__(self):
        return f"<Prediction(match_id={self.match_id}, type={self.developer_name}, selection={self.selection})>"

class Odd(Base):
    """Odd model for match betting odds"""
    __tablename__ = 'odds'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey('matches.id'), nullable=False, index=True)
    bookmaker_id = Column(Integer, nullable=False)
    bookmaker_name = Column(String(255), nullable=True)
    market_id = Column(Integer, nullable=True)
    market_name = Column(String(255), nullable=False)
    normalized_market = Column(String(100), nullable=True, index=True)
    selection_id = Column(Integer, nullable=True)
    selection_name = Column(String(255), nullable=False)
    normalized_selection = Column(String(100), nullable=True)
    value = Column(Float, nullable=False)
    implied_probability = Column(Float, nullable=True)
    is_live = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    match = relationship("Match", back_populates="odds")
    
    # Unique constraint to avoid duplicates
    __table_args__ = (UniqueConstraint('match_id', 'bookmaker_id', 'market_name', 'selection_name',
                                      name='unique_odd'),)
    
    def __repr__(self):
        return f"<Odd(match_id={self.match_id}, bookmaker={self.bookmaker_name}, market={self.market_name})>"

# Create all tables
def create_tables():
    try:
        Base.metadata.create_all(engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {str(e)}")
        raise
