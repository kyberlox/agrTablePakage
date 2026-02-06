from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base



class Calculated(Base):
    __tablename__ = 'calculated'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    operation = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parameter_1_id = Column(Integer, ForeignKey("parameters.id"), nullable=False)  # Связь через внешний ключ
    parameter_2_id = Column(Integer, ForeignKey("parameters.id"), nullable=False)  # Связь через внешний ключ

    parameter = relationship("ParameterSchema", back_populates="calculated")  # Связь через обратное отношение с Parameter, чтобы обеспечить обратную связь с таблицей Parameter
