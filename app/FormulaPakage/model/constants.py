from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
# from .database import Base
from app.TablePakage.model.database import Base


class Constants(Base):
    __tablename__ = 'constants'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    value = Column(Float, nullable=True)
    result_param_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=False)

    # Связь через обратное отношение с парамтером, чтобы обеспечить обратную связь с таблицей ParameterSchema
    
    result_parameter = relationship(
        "ParameterSchema",
        foreign_keys=[result_param_id],
        back_populates="constants"
    )