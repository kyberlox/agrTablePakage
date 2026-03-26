from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey
from sqlalchemy.orm import relationship
# from .database import Base
from app.TablePakage.model.database import Base

class SelectedFile(Base):
    __tablename__ = 'selected_file'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=True)
    content_type = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    file_url = Column(Text, nullable=True)
    result_param_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=False)

    selected_file_parametr_schema = relationship("ParameterSchema", back_populates="selected_files")
