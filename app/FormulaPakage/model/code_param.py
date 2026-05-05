from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey
from sqlalchemy.orm import relationship
# from .database import Base
from app.TablePakage.model.database import Base



class CodeParam(Base):
    __tablename__ = 'codeparam'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=True)
    description = Column(String(255), nullable=True)
    
    function_name = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # parameter_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=True)  # Связь через внешний ключ
    # parameter_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=True)  # Связь через внешний ключ
    result_param_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=False)
    
    # first_parameter = relationship(
    #     "ParameterSchema", 
    #     foreign_keys=[parameter_id],
    #     back_populates="calculations_as_first_param"
    # )
    
    # second_parameter = relationship(
    #     "ParameterSchema", 
    #     foreign_keys=[parameter_2_id],
    #     back_populates="calculations_as_second_param"
    # )
    
    result_parameter = relationship(
        "ParameterSchema", 
        foreign_keys=[result_param_id],
        back_populates="code_as_result"
    )