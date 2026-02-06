from sqlalchemy import Column, Integer, String, Text, Float, DateTime, func
from .database import Base



class UserInput(Base):
    __tablename__ = "user_input"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(255))
    min_value = Column(Float)
    max_value = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    parametr_schema_id = Column(Integer, ForeignKey("parameter_schemas.id"), nullable=False)


    user_input_parametr_schema = relationship("ParameterSchema", back_populates="user_inputs")
