"""Memory data models."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import Field, ConfigDict
from bson import ObjectId

from .base import BaseModel, DocumentBase


class MemoryCreate(BaseModel):
    """Memory creation model."""
    agent_id: str = Field(..., description="智能体ID")
    task_id: Optional[str] = Field(None, description="关联的任务ID")
    title: str = Field(..., description="记忆标题")
    raw_text: str = Field(..., description="记忆的原始文本内容(对于对于复杂任务或者容易出错的情况需要要详细记录)")
    goal: str = Field(..., description="当前Task或者Todo的目标")
    actions: List[str] = Field(default_factory=list, description="执行的操作")
    outcome: str = Field(..., description="执行的结果")
    beneficial_ops: List[str] = Field(default_factory=list, description="有益操作")
    improvements: List[str] = Field(default_factory=list, description="改进建议")
    suggestions: Optional[str] = Field(None, description="下次做类似的Task或Todo, 可以参考的内容")
    tags: List[str] = Field(default_factory=list, description="标签列表, 用于分类和检索, 3-5个关键词")
    session_id: Optional[str] = Field(None, description="会话ID, 描述记忆来源那次会话")


class MemoryUpdate(BaseModel):
    """Memory update model."""

    title: Optional[str] = Field(None, description="记忆标题")
    raw_text: Optional[str] = Field(None, description="记忆的原始文本内容")
    goal: Optional[str] = Field(None, description="目标")
    actions: Optional[List[str]] = Field(None, description="执行的操作")
    outcome: Optional[str] = Field(None, description="结果")
    beneficial_ops: Optional[List[str]] = Field(None, description="有益操作")
    improvements: Optional[List[str]] = Field(None, description="改进建议")
    suggestions: Optional[str] = Field(None, description="建议")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    session_id: Optional[str] = Field(None, description="会话ID, 描述记忆来源那次会话")


class Memory(DocumentBase):
    """Memory model as stored in database."""
    
    id: str = Field(default_factory=lambda: str(ObjectId()), alias="_id")
    project_id: str = Field(..., description="项目ID")
    agent_id: str = Field(..., description="智能体ID")
    task_id: Optional[str] = Field(None, description="关联的任务ID")
    title: str = Field(..., description="记忆标题")
    raw_text: str = Field(..., description="原始文本内容")
    goal: Optional[str] = Field(None, description="目标")
    actions: List[str] = Field(default_factory=list, description="执行的操作")
    outcome: Optional[str] = Field(None, description="结果")
    beneficial_ops: List[str] = Field(default_factory=list, description="有益操作")
    improvements: List[str] = Field(default_factory=list, description="改进建议")
    suggestions: Optional[str] = Field(None, description="建议")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    embedding_model: Optional[str] = Field(None, description="嵌入模型")
    embedding: Optional[List[float]] = Field(None, description="嵌入向量")
    chunks: List[Dict[str, Any]] = Field(default_factory=list, description="文本分块")
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc))
    session_id: Optional[str] = Field(None, description="会话ID, 描述记忆来源那次会话")
    model_config = ConfigDict(validate_by_name=True)