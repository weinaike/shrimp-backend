"""Memory management tools for MCP server.

This module provides comprehensive memory management functionality including:
- CRUD operations for memories
- Search and filtering capabilities
- Tag-based organization
- Task association
- Verification status tracking
"""

from tokenize import Name
import traceback
from typing import Annotated, Any, Dict, List, Optional
from fastmcp import FastMCP

from shrimp.models.memory import MemoryCreate, MemoryUpdate
from shrimp.services.memory_service import MemoryService
from shrimp.db.database import mcp_db_manager
from .base_tool import BaseTool
from .response_format import MCPToolResponse


async def get_mcp_memory_service():
    """Get MemoryService instance with MCP database connection."""
    if mcp_db_manager.database is None:
        await mcp_db_manager.connect_to_mongo()
    return MemoryService(mcp_db_manager.database)


def register_memory_tools(app: FastMCP):
    """Register all memory-related tools with the FastMCP application.
    
    Args:
        app: The FastMCP application instance to register tools with
    """
    
    @app.tool
    async def add_memory(memory_create: MemoryCreate) -> Dict[str, Any]:
        """添加新记忆
        
        智能体接口说明：
        - 功能：在项目中创建新的知识记忆条目
        - 输入：MemoryCreate对象，包含记忆的内容、标签、关联任务等
        - 输出：创建成功的记忆对象，包含生成的memory_id
        - 项目隔离：自动从请求头获取project_id
        - 用途：智能体保存重要的知识点、解决方案、经验总结
        - 特性：支持标签分类、任务关联、向量搜索
        """
        memory_service = await get_mcp_memory_service()
        project_id = BaseTool.get_project_id()
        
        try:
            memory = await memory_service.create_memory(project_id, memory_create)
            return MCPToolResponse.success(
                data=memory.model_dump(),
                operation="add_memory",
                message=f"Successfully created memory with {len(memory_create.tags)} tags. you can do NEXT todo or task if have",
            )
        except Exception as e:
            error_detail = traceback.format_exc()
            return MCPToolResponse.error(
                operation="add_memory",
                error_message=f"Failed to add memory: {str(e)}\n{error_detail}\nPlease carefully check the tool interface description and strictly follow the parameter specifications to call the tool",
                metadata={"project_id": project_id}
            )


    @app.tool
    async def query_memories(
        task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        q: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """列出项目中的记忆（支持多维度过滤和分页）
        
        智能体接口说明：
        - 功能：获取项目中的记忆列表，支持多种过滤条件
        - 输入：可选的任务ID、标签、文本搜索、验证状态等过滤器
        - 输出：符合条件的记忆列表
        - 项目隔离：只返回当前项目的记忆
        - 搜索能力：支持文本搜索和向量相似性搜索
        - 用途：智能体检索相关知识，进行RAG（检索增强生成）
        
        Args:
            task_id (Optional[str]): Filter memories associated with specific task
            tags (Optional[List[str]]): Filter memories by tags
            q (Optional[str]): Text search query for content matching
            skip (int): Number of memories to skip for pagination (default: 0)
            limit (int): Maximum number of memories to return (default: 100)
            
        Returns:
            list[dict]: List of memory objects matching the criteria
            
        """
        memory_service = await get_mcp_memory_service()
        project_id = BaseTool.get_project_id()
        
        try:
            memories = await memory_service.list_memories(
                project_id=project_id,
                task_id=task_id,
                tags=tags,
                q=q,
                skip=skip,
                limit=limit,
            )
            
            result = [memory.model_dump() for memory in memories] if memories else []
            
            return MCPToolResponse.success(
                data=result,
                operation="query_memories",
                message=f"Found {len(result)} memories",
                metadata={
                    "project_id": project_id,
                    "filters": {
                        "task_id": task_id,
                        "tags": tags,
                        "query": q,
                        "skip": skip,
                        "limit": limit
                    },
                    "total_found": len(result)
                }
            )
        except Exception as e:
            error_detail = traceback.format_exc()
            return MCPToolResponse.error(
                operation="query_memories",
                error_message=f"Failed to query memories: {str(e)}\n{error_detail}\nPlease carefully check the tool interface description and strictly follow the parameter specifications to call the tool",
                metadata={
                    "project_id": project_id,
                    "filters": {
                        "task_id": task_id,
                        "tags": tags,
                        "query": q,
                        "skip": skip,
                        "limit": limit
                    }
                }
            )

