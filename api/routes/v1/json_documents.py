"""JSON Document API endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from bson import ObjectId

from shrimp.models.json_document import (
    JsonDocument, 
    JsonDocumentCreate, 
    JsonDocumentQuery,
    JsonDocumentBatch,
    DocumentType
)

from shrimp.services.json_document_service import JsonDocumentService
from shrimp.api.dependencies import get_current_project
from shrimp.api.utils import handle_service_response

router = APIRouter()


# ==================== CRUD Operations ====================

@router.post("/{project_id}/json-documents", response_model=JsonDocument)
async def create_json_document(
    project_id: str = Path(..., description="项目ID"),
    document: JsonDocumentCreate = Body(..., description="文档创建数据"),
    current_project: str = Depends(get_current_project)
):
    """创建JSON文档。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.create_document(project_id, document, created_by=current_project)
    return handle_service_response(response)


@router.get("/{project_id}/json-documents/{document_id}", response_model=JsonDocument)
async def get_json_document(
    project_id: str = Path(..., description="项目ID"),
    document_id: str = Path(..., description="文档ID"),
    increment_access: bool = Query(True, description="是否增加访问计数"),
    current_project: str = Depends(get_current_project)
):
    """获取JSON文档详情。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.get_document(project_id, document_id, increment_access)
    return handle_service_response(response)


@router.delete("/{project_id}/json-documents/{document_id}")
async def delete_json_document(
    project_id: str = Path(..., description="项目ID"),
    document_id: str = Path(..., description="文档ID"),
    current_project: str = Depends(get_current_project)
):
    """删除JSON文档。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.delete_document(project_id, document_id, deleted_by=current_project)
    return handle_service_response(response)


# ==================== Query Operations ====================

@router.get("/{project_id}/json-documents", response_model=List[JsonDocument])
async def list_json_documents(
    project_id: str = Path(..., description="项目ID"),
    name_pattern: str = Query(None, description="名称模式匹配"),
    document_type: DocumentType = Query(None, description="文档类型过滤"),
    session_id: str = Query(None, description="会话ID过滤"),
    tags: List[str] = Query(None, description="标签过滤"),
    is_public: bool = Query(None, description="公开状态过滤"),
    content_search: str = Query(None, description="内容搜索关键词"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(20, ge=1, le=100, description="返回记录数"),
    sort_by: str = Query("updated_at", description="排序字段"),
    sort_order: int = Query(-1, description="排序顺序 (1: 升序, -1: 降序)"),
    current_project: str = Depends(get_current_project)
):
    """获取JSON文档列表，支持多种过滤条件。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = JsonDocumentQuery(
        name_pattern=name_pattern,
        document_type=document_type,
        session_id=session_id,
        tags=tags or [],
        is_public=is_public,
        content_search=content_search,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    service = JsonDocumentService()
    response = await service.list_documents(project_id, query)
    return handle_service_response(response)


@router.post("/{project_id}/json-documents/search", response_model=List[JsonDocument])
async def search_json_documents(
    project_id: str = Path(..., description="项目ID"),
    search_terms: List[str] = Body(..., description="搜索关键词列表"),
    document_type: DocumentType = Body(None, description="文档类型过滤"),
    limit: int = Body(20, ge=1, le=100, description="返回结果数量"),
    current_project: str = Depends(get_current_project)
):
    """高级内容搜索，支持多个关键词。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.search_documents_by_content(project_id, search_terms, document_type, limit)
    return handle_service_response(response)


# ==================== Session-based Operations ====================

@router.get("/{project_id}/sessions/{session_id}/documents", response_model=List[JsonDocument])
async def get_session_documents(
    project_id: str = Path(..., description="项目ID"),
    session_id: str = Path(..., description="会话ID"),
    document_type: Optional[DocumentType] = Query(None, description="文档类型"),
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回记录数"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: int = Query(1, description="排序顺序 (1: 升序, -1: 降序)"),
    current_project: str = Depends(get_current_project)
):
    """获取指定会话的所有文档。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.get_documents_by_session(
        project_id, session_id, document_type, skip, limit, sort_by, sort_order
    )
    return handle_service_response(response)


@router.get("/{project_id}/sessions/{session_id}/statistics")
async def get_session_statistics(
    project_id: str = Path(..., description="项目ID"),
    session_id: str = Path(..., description="会话ID"),
    current_project: str = Depends(get_current_project)
):
    """获取指定会话的统计信息。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.get_session_statistics(project_id, session_id)
    return handle_service_response(response)


@router.delete("/{project_id}/sessions/{session_id}/documents")
async def delete_session_documents(
    project_id: str = Path(..., description="项目ID"),
    session_id: str = Path(..., description="会话ID"),
    current_project: str = Depends(get_current_project)
):
    """删除指定会话的所有文档。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.delete_session_documents(project_id, session_id, deleted_by=current_project)
    return handle_service_response(response)


@router.get("/{project_id}/sessions")
async def list_sessions(
    project_id: str = Path(..., description="项目ID"),
    current_project: str = Depends(get_current_project)
):
    """获取项目中所有活跃会话列表。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    
    # Get distinct session IDs with document counts
    pipeline = [
        {"$match": {"project_id": project_id}},
        {
            "$group": {
                "_id": "$session_id",
                "document_count": {"$sum": 1},
                "last_updated": {"$max": "$updated_at"},
                "first_created": {"$min": "$created_at"},
                "total_access_count": {"$sum": "$access_count"}
            }
        },
        {"$sort": {"last_updated": -1}}
    ]
    
    try:
        db = service.db
        result = await db[service.collection_name].aggregate(pipeline).to_list(length=None)
        
        sessions = []
        for item in result:
            sessions.append({
                "session_id": item["_id"],
                "document_count": item["document_count"],
                "last_updated": item["last_updated"],
                "first_created": item["first_created"],
                "total_access_count": item["total_access_count"]
            })
        
        return {
            "sessions": sessions,
            "total_sessions": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


# ==================== Batch Operations ====================

@router.post("/{project_id}/json-documents/batch")
async def batch_json_documents_operation(
    project_id: str = Path(..., description="项目ID"),
    batch: JsonDocumentBatch = Body(..., description="批量操作数据"),
    current_project: str = Depends(get_current_project)
):
    """执行批量操作：删除、更新标签、更新类型、设置公开状态。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.batch_operation(project_id, batch, operator=current_project)
    return handle_service_response(response)


# ==================== Statistics and Analytics ====================

@router.get("/{project_id}/json-documents/statistics")
async def get_json_documents_statistics(
    project_id: str = Path(..., description="项目ID"),
    current_project: str = Depends(get_current_project)
):
    """获取JSON文档统计信息。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.get_document_statistics(project_id)
    return handle_service_response(response)


# ==================== Utility Endpoints ====================

@router.get("/{project_id}/json-documents/types")
async def get_document_types():
    """获取所有支持的文档类型。"""
    types = [{"value": dt.value, "label": dt.value.replace("_", " ").title()} for dt in DocumentType]
    return {"types": types}


@router.post("/{project_id}/json-documents/{document_id}/validate-schema")
async def validate_document_schema(
    project_id: str = Path(..., description="项目ID"),
    document_id: str = Path(..., description="文档ID"),
    schema: Dict[str, Any] = Body(..., description="JSON Schema"),
    current_project: str = Depends(get_current_project)
):
    """验证文档内容是否符合指定的JSON Schema。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    
    # First get the document
    doc_response = await service.get_document(project_id, document_id, increment_access=False)
    if not doc_response.success:
        return handle_service_response(doc_response)
    
    document = doc_response.data
    
    try:
        import jsonschema
        jsonschema.validate(document.content, schema)
        return {"valid": True, "message": "文档内容符合Schema规范"}
    except jsonschema.ValidationError as e:
        return {"valid": False, "message": f"Schema验证失败: {e.message}"}
    except jsonschema.SchemaError as e:
        return {"valid": False, "message": f"无效的JSON Schema: {e.message}"}


@router.get("/{project_id}/json-documents/{document_id}/content-only")
async def get_document_content_only(
    project_id: str = Path(..., description="项目ID"),
    document_id: str = Path(..., description="文档ID"),
    current_project: str = Depends(get_current_project)
):
    """仅获取文档的JSON内容，不包含元数据。"""
    if project_id != current_project:
        raise HTTPException(status_code=403, detail="Access denied")
    
    service = JsonDocumentService()
    response = await service.get_document(project_id, document_id, increment_access=True)
    
    if not response.success:
        return handle_service_response(response)
    
    return response.data.content
