import datetime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DB_URI

engine = create_engine(DB_URI)
sqlSession = sessionmaker(bind=engine)
db = sqlSession()

Base = declarative_base()

class Sites(Base):
    __tablename__ = 'sites'
    id = Column(Integer, primary_key=True)
    domain = Column(String(255))
    site_type = Column(Integer)
    valid = Column(Boolean)
    # status_code = Column(Integer)
    title = Column(String(64))
    ip = Column(String(32))
    port = Column(Integer)
    country = Column(String(2))
    city = Column(String(32))
    asn = Column(String(64))
    sign = Column(String(32))
    protocol = Column(String(8))
    cert = Column(Text())
    cert_version = Column(Integer)
    cert_subject_country = Column(String(2))
    cert_subject_stateOrProvinceName = Column(String(64))
    cert_subject_localityName = Column(String(64))
    cert_subject_organization = Column(String(64))
    cert_subject_common_name = Column(String(64))
    cert_issuer_country = Column(String(2))
    cert_issuer_organization = Column(String(64))
    cert_issuer_common_name = Column(String(64))
    cert_not_before = Column(DateTime)
    cert_not_after = Column(DateTime)
    create_time = Column(DateTime, default=datetime.datetime.now)
    
def initDatabase():
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    initDatabase()