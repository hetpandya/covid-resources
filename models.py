from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, SmallInteger, Boolean,ForeignKey,BigInteger,DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import select
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker
import json,os

root = os.getcwd()

try:
    with open(os.path.join(root,"creds.json")) as json_file:
    	creds = json.load(json_file)
except:
    with open(os.path.join(root,"/home/hetpandy/public_html/flask/creds.json")) as json_file:
    	creds = json.load(json_file)

engine = create_engine(f'mysql://{creds["db_user"]}:{creds["db_password"]}@{creds["db_ip"]}/{creds["db_name"]}', echo = True)
meta = MetaData()

con = engine.connect()

Base = declarative_base()

class Resources(Base):
    __tablename__ = 'resources'
   
    id = Column(Integer, primary_key = True)
    resource_type = Column(SmallInteger)
    available = Column(Boolean)
    verified = Column(Boolean)
    is_approved_by_admin = Column(Boolean)
    state_id = Column(SmallInteger)
    city_id = Column(SmallInteger)
    resource_count = Column(SmallInteger)
    donor_or_recipient = Column(Boolean)
    media_id = Column(Integer,ForeignKey('media.id'))
    last_updated = Column(DateTime)
    additional_information = Column(String)
    

class Donors(Base):
    __tablename__ = 'donors'
   
    id = Column(Integer, primary_key = True)
    name = Column(String)
    resource_id = Column(Integer,ForeignKey('resources.id', ondelete='CASCADE'))
    resources = relationship("Resources",backref ="available_donors")
    contact = Column(String)
    blood_group = Column(String)
    address = Column(String)

class Recipients(Base):
    __tablename__ = 'recipients'
   
    id = Column(Integer, primary_key = True)
    name = Column(String)
    resource_id = Column(Integer,ForeignKey('resources.id', ondelete='CASCADE'))
    resources = relationship("Resources",backref ="resource_recipients")
    contact = Column(String)
    blood_group = Column(String)
    address = Column(String)
    receive_notifications = Column(Boolean)
    receive_notifications_all_cities = Column(Boolean)
    
class Media(Base):
    __tablename__ = 'media'
    
    id = Column(Integer, primary_key = True)
    resources = relationship("Resources",backref ="source_media") 
    url = Column(String)
    local_storage = Column(String)

class InAppropriateResources(Base):
    __tablename__ = 'inappropriate_resources'
    
    id = Column(Integer, primary_key = True)
    resource_id = Column(Integer,ForeignKey('resources.id'))
    comment = Column(String)

class Registrations(Base):
    __tablename__ = 'registrations'
    
    id = Column(Integer, primary_key = True)
    otp = Column(Integer)
    contact = Column(String)
    number_verified = Column(Boolean)

class UserRegistrations(Base):
    __tablename__ = 'user_registration'
    
    id = Column(Integer, primary_key = True)
    otp = Column(Integer)
    username = Column(String)


class User(Base):
    __tablename__ = 'user'
  
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True)
    password = Column(String(80))
    number_verified = Column(Boolean)
    contact = Column(String)

Session = sessionmaker(bind = engine)
db_session = Session()