# app/products/model/parameter_schema.py
from sqlalchemy import Column, Integer, String, Text, DateTime, func, JSON, ForeignKey, Index, UniqueConstraint, Boolean
from sqlalchemy.orm import relationship
from .database import Base 

class ParameterSchema(Base):
    __tablename__ = "parameter_schemas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    transliterated_name = Column(String(255), nullable=False)
    description = Column(Text)
    type = Column(String(50), nullable=False)  # "Table" или "Formula"
    measuring_unit = Column(Text, nullable=True) # Единицы измерения
    visibility = Column(Boolean, default=True) #Видимость для пользователя
    required_type = Column(Text, default='list')  # Тип данных для типа "Formula"
    table_name = Column(String(255))  # Имя таблицы для типа "Table"
    field_of_view = Column(JSON, default=dict)  # Хранение JSON: {"admin": true, "user": false}
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # Связь через внешний ключ

    # ORM-связь
    product = relationship("Product", back_populates="parameters")

    # Связь с user_input
    user_inputs = relationship("UserInput", foreign_keys="[UserInput.result_param_id]", back_populates="user_input_parametr_schema", cascade="all, delete-orphan")
 
    # Связь с conditions
    conditions = relationship(
        "Conditions",
        foreign_keys="[Conditions.condition_param_id]",
        back_populates="conditions_parameter",
        cascade="all, delete-orphan"
    )

    result_conditions = relationship(
        "Conditions", 
        foreign_keys="[Conditions.result_param_id]", 
        back_populates="result_parameter", 
        cascade="all, delete-orphan"
    )

    # Связь с selected_file
    selected_files = relationship(
        "SelectedFile", 
        foreign_keys="[SelectedFile.result_param_id]", 
        back_populates="selected_file_parametr_schema", 
        cascade="all, delete-orphan"
    )

    # Связь с формулами
    calculations_as_first_param = relationship(
        "Calculated", 
        foreign_keys="[Calculated.parameter_id]",
        back_populates="first_parameter",
        cascade="all, delete-orphan"
    )
    
    # calculations_as_second_param = relationship(
    #     "Calculated", 
    #     foreign_keys="[Calculated.parameter_2_id]",
    #     back_populates="second_parameter",
    #     cascade="all, delete-orphan"
    # )
    
    calculations_as_result = relationship(
        "Calculated", 
        foreign_keys="[Calculated.result_param_id]",
        back_populates="result_parameter",
        cascade="all, delete-orphan"
    )

    # Связь с conditions
    constants = relationship(
        "Constants",
        foreign_keys="[Constants.result_param_id]",
        back_populates="result_parameter",
        cascade="all, delete-orphan"
    )

    # Новая связь для CodeParam
    # Имя должно совпадать с тем, что указано в back_populates модели CodeParam
    code_as_result = relationship(
        "CodeParam",
        back_populates="result_parameter"   # это имя отношения в CodeParam
    )

    __table_args__ = (
        Index("idx_parameter_product_id", "product_id"),
        UniqueConstraint("product_id", "transliterated_name", name="uq_product_parameter"),
    )