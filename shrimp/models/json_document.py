"""JSON document data models."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator
from bson import ObjectId

from .base import DocumentBase, PyObjectId


class DocumentType(str, Enum):
    """Document type enumeration."""
    AGENT_COMPONENT_MODEL = "agent_component_model"
    SESSION_STATE = "session_state"
    OTHER = "other"


class JsonDocumentCreate(BaseModel):
    """JSON document creation model."""
    name: str = Field(..., description="文档名称", min_length=1, max_length=200)
    description: Optional[str] = Field(None, description="文档描述", max_length=1000)
    document_type: DocumentType = Field(DocumentType.OTHER, description="文档类型")
    content: Dict[str, Any] = Field(..., description="JSON内容")
    session_id: str = Field(..., description="会话ID", min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    is_public: bool = Field(False, description="是否公开")
    schema_validation: Optional[Dict[str, Any]] = Field(None, description="JSON Schema验证规则")

    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate tags."""
        if len(v) > 20:
            raise ValueError("标签数量不能超过20个")
        return [tag.strip() for tag in v if tag.strip()]

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Validate name."""
        return v.strip()

    @field_validator('session_id')
    @classmethod
    def validate_session_id(cls, v):
        """Validate session_id."""
        return v.strip()

class JsonDocument(DocumentBase):
    """JSON document model as stored in database."""
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str = Field(..., description="项目ID")
    name: str = Field(..., description="文档名称")
    description: Optional[str] = Field(None, description="文档描述")
    document_type: DocumentType = Field(..., description="文档类型")
    content: Dict[str, Any] = Field(..., description="JSON内容")
    session_id: str = Field(..., description="会话ID")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    is_public: bool = Field(default=False, description="是否公开")
    schema_validation: Optional[Dict[str, Any]] = Field(None, description="JSON Schema验证规则")
    
   
    # Audit fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(), description="创建时间")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(), description="更新时间")
    created_by: str = Field(default="system", description="创建者")
    updated_by: str = Field(default="system", description="更新者")
    
    # Statistics
    access_count: int = Field(default=0, description="访问次数")
    last_accessed_at: Optional[datetime] = Field(None, description="最后访问时间")

    model_config = ConfigDict(
        json_encoders={ObjectId: str},
        validate_by_name=True,
        use_enum_values=True,
        populate_by_name=True
    )


class JsonDocumentQuery(BaseModel):
    """JSON document query model."""
    name_pattern: Optional[str] = Field(None, description="名称模式匹配")
    document_type: Optional[DocumentType] = Field(None, description="文档类型")
    session_id: Optional[str] = Field(None, description="会话ID过滤")
    tags: Optional[List[str]] = Field(None, description="标签过滤")
    is_public: Optional[bool] = Field(None, description="公开状态过滤")
    content_search: Optional[str] = Field(None, description="内容搜索")
    created_after: Optional[datetime] = Field(None, description="创建时间过滤(之后)")
    created_before: Optional[datetime] = Field(None, description="创建时间过滤(之前)")
    updated_after: Optional[datetime] = Field(None, description="更新时间过滤(之后)")
    updated_before: Optional[datetime] = Field(None, description="更新时间过滤(之前)")
    skip: int = Field(0, ge=0, description="跳过记录数")
    limit: int = Field(20, ge=1, le=100, description="返回记录数")
    sort_by: str = Field("updated_at", description="排序字段")
    sort_order: int = Field(-1, description="排序顺序 (1: 升序, -1: 降序)")


class JsonDocumentBatch(BaseModel):
    """Batch operations model."""
    document_ids: List[str] = Field(..., description="文档ID列表")
    operation: str = Field(..., description="操作类型: delete, update_tags, update_type, set_public")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="操作参数")
