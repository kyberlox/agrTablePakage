from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
# from .database import Base
from app.TablePakage.model.database import Base



class UserInput(Base):
    __tablename__ = "user_input"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    type = Column(String(255))
    min_value = Column(Float)
    max_value = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    result_param_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=False)


    user_input_parametr_schema = relationship("ParameterSchema", back_populates="user_inputs")
