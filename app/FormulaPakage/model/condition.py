from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
# from .database import Base
from app.TablePakage.model.database import Base


class Conditions(Base):
    __tablename__ = 'conditions'

    id = Column(Integer, primary_key=True)
    condition_param_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=True)
    condition_operator = Column(Text, nullable=True) 
    condition_value = Column(Text, nullable=True) 
    result_value = Column(Text, nullable=True) 
    result_value_type = Column(Boolean, nullable=True)
    result_param_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=False)

    # Связь через обратное отношение с парамтером, чтобы обеспечить обратную связь с таблицей ParameterSchema
    conditions_parameter = relationship(
        "ParameterSchema",
        foreign_keys=[condition_param_id],
        back_populates="conditions"
    )  
    result_parameter = relationship(
        "ParameterSchema",
        foreign_keys=[result_param_id],
        back_populates="result_conditions"
    )