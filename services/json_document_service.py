"""JSON Document service for business logic."""

import json
import re
import hashlib
from typing import List, Optional, Dict, Any, cast
from datetime import datetime, timezone
from bson import ObjectId, errors as bson_errors
import jsonschema
from jsonschema import ValidationError

from shrimp.models.json_document import (
    JsonDocument, 
    JsonDocumentCreate, 
    JsonDocumentQuery,
    JsonDocumentBatch,
    DocumentType
)

from shrimp.db.database import get_database, MCPDatabase
from shrimp.core.response import ServiceResponse

class JsonDocumentService:
    """Service for managing JSON documents with full CRUD operations."""
    
    def __init__(self, database: Optional[MCPDatabase] = None):
        self.db: MCPDatabase = database if database is not None else cast(MCPDatabase, get_database())
        self.collection_name = "json_documents"

    # ==================== Core CRUD Operations ====================
    
    async def create_document(
        self, 
        project_id: str, 
        document_create: JsonDocumentCreate,
        created_by: str = "system"
    ) -> ServiceResponse[JsonDocument]:
        """Create a new JSON document."""
        try:
            # Validate JSON schema if provided
            if document_create.schema_validation:
                try:
                    jsonschema.Draft7Validator.check_schema(document_create.schema_validation)
                    # Test the content against the schema
                    jsonschema.validate(document_create.content, document_create.schema_validation)
                except ValidationError as e:
                    return ServiceResponse.validation_error(f"JSON Schema验证失败: {e.message}")
                except jsonschema.SchemaError as e:
                    return ServiceResponse.validation_error(f"无效的JSON Schema: {e.message}")

            # Prepare document data
            current_time = datetime.now()
            
            document_data = {
                **document_create.model_dump(),
                "project_id": project_id,
                "created_at": current_time,
                "updated_at": current_time,
                "created_by": created_by,
                "updated_by": created_by,
                "access_count": 0,
                "last_accessed_at": None
            }

            # Insert document
            result = await self.db[self.collection_name].insert_one(document_data)
            document_data["_id"] = str(result.inserted_id)  # Convert ObjectId to string

            # Convert to model
            document = JsonDocument(**document_data)
            
            return ServiceResponse.success_response(document, "文档创建成功")

        except Exception as e:
            return ServiceResponse.error_response(f"创建文档失败: {str(e)}")

    async def get_document(
        self, 
        project_id: str, 
        document_id: str,
        increment_access: bool = True
    ) -> ServiceResponse[JsonDocument]:
        """Get a JSON document by ID."""
        try:
            if not ObjectId.is_valid(document_id):
                return ServiceResponse.validation_error("无效的文档ID")

            # Find document
            document_data = await self.db[self.collection_name].find_one({
                "_id": ObjectId(document_id),
                "project_id": project_id
            })

            if not document_data:
                return ServiceResponse.not_found("文档不存在")

            # Increment access count if requested
            if increment_access:
                await self.db[self.collection_name].update_one(
                    {"_id": ObjectId(document_id)},
                    {
                        "$inc": {"access_count": 1},
                        "$set": {"last_accessed_at": datetime.now()}
                    }
                )
                document_data["access_count"] = document_data.get("access_count", 0) + 1
                document_data["last_accessed_at"] = datetime.now()

            # Convert ObjectId to string for the model
            document_data["_id"] = str(document_data["_id"])
            document = JsonDocument(**document_data)
            return ServiceResponse.success_response(document, "获取文档成功")

        except Exception as e:
            return ServiceResponse.error_response(f"获取文档失败: {str(e)}")


    async def delete_document(
        self, 
        project_id: str, 
        document_id: str,
        deleted_by: str = "system"
    ) -> ServiceResponse[bool]:
        """Delete a JSON document."""
        try:
            if not ObjectId.is_valid(document_id):
                return ServiceResponse.validation_error("无效的文档ID")

            # Check if document exists
            existing_doc = await self.db[self.collection_name].find_one({
                "_id": ObjectId(document_id),
                "project_id": project_id
            })

            if not existing_doc:
                return ServiceResponse.not_found("文档不存在")

            # Delete document
            result = await self.db[self.collection_name].delete_one({
                "_id": ObjectId(document_id)
            })

            if result.deleted_count == 0:
                return ServiceResponse.error_response("文档删除失败")

            return ServiceResponse.success_response(True, "文档删除成功")

        except Exception as e:
            return ServiceResponse.error_response(f"删除文档失败: {str(e)}")

    # ==================== Query Operations ====================
    
    async def list_documents(
        self, 
        project_id: str, 
        query: JsonDocumentQuery
    ) -> ServiceResponse[List[JsonDocument]]:
        """List documents with filtering and pagination."""
        try:
            # Build MongoDB query
            mongo_query = {"project_id": project_id}
            
            # Name pattern matching
            if query.name_pattern:
                mongo_query["name"] = {"$regex": re.escape(query.name_pattern), "$options": "i"}
            
            # Document type filter
            if query.document_type:
                mongo_query["document_type"] = query.document_type
            
            # Session ID filter
            if query.session_id:
                mongo_query["session_id"] = query.session_id
            
            # Tags filter
            if query.tags:
                mongo_query["tags"] = {"$in": query.tags}
            
            # Public filter
            if query.is_public is not None:
                mongo_query["is_public"] = query.is_public
            
            # Content search (full-text search in JSON content)
            if query.content_search:
                # Convert content to string and search
                mongo_query["$expr"] = {
                    "$regexMatch": {
                        "input": {"$toString": "$content"},
                        "regex": re.escape(query.content_search),
                        "options": "i"
                    }
                }
            
            # Date filters
            if query.created_after or query.created_before:
                date_filter = {}
                if query.created_after:
                    date_filter["$gte"] = query.created_after
                if query.created_before:
                    date_filter["$lte"] = query.created_before
                mongo_query["created_at"] = date_filter
            
            if query.updated_after or query.updated_before:
                date_filter = {}
                if query.updated_after:
                    date_filter["$gte"] = query.updated_after
                if query.updated_before:
                    date_filter["$lte"] = query.updated_before
                mongo_query["updated_at"] = date_filter

            # Execute query with pagination and sorting
            cursor = self.db[self.collection_name].find(mongo_query)
            cursor = cursor.sort(query.sort_by, query.sort_order)
            cursor = cursor.skip(query.skip).limit(query.limit)
            
            documents_data = await cursor.to_list(length=None)
            # Convert ObjectId to string for each document
            for doc in documents_data:
                doc["_id"] = str(doc["_id"])
            documents = [JsonDocument(**doc) for doc in documents_data]
            
            return ServiceResponse.success_response(documents, f"找到 {len(documents)} 个文档")

        except Exception as e:
            return ServiceResponse.error_response(f"查询文档失败: {str(e)}")

    async def search_documents_by_content(
        self, 
        project_id: str, 
        search_terms: List[str],
        document_type: Optional[DocumentType] = None,
        limit: int = 20
    ) -> ServiceResponse[List[JsonDocument]]:
        """Advanced content search in JSON documents."""
        try:
            # Build search query
            mongo_query = {"project_id": project_id}
            
            if document_type:
                mongo_query["document_type"] = document_type
            
            # Create regex for search terms
            if search_terms:
                search_conditions = []
                for term in search_terms:
                    search_conditions.append({
                        "$expr": {
                            "$regexMatch": {
                                "input": {"$toString": "$content"},
                                "regex": re.escape(term),
                                "options": "i"
                            }
                        }
                    })
                
                if len(search_conditions) == 1:
                    mongo_query.update(search_conditions[0])
                else:
                    mongo_query["$and"] = search_conditions

            # Execute search
            cursor = self.db[self.collection_name].find(mongo_query)
            cursor = cursor.sort("updated_at", -1).limit(limit)
            
            documents_data = await cursor.to_list(length=None)
            # Convert ObjectId to string for each document
            for doc in documents_data:
                doc["_id"] = str(doc["_id"])
            documents = [JsonDocument(**doc) for doc in documents_data]
            
            return ServiceResponse.success_response(documents, f"搜索到 {len(documents)} 个相关文档")

        except Exception as e:
            return ServiceResponse.error_response(f"搜索文档失败: {str(e)}")

    async def get_documents_by_session(
        self, 
        project_id: str, 
        session_id: str,
        document_type: Optional[DocumentType] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: int = 1
    ) -> ServiceResponse[List[JsonDocument]]:
        """Get all documents for a specific session."""
        try:
            # Build query for session
            mongo_query = {
                "project_id": project_id,
                "session_id": session_id
            }
            
            if document_type:
                mongo_query["document_type"] = document_type

            # Execute query with pagination and sorting
            cursor = self.db[self.collection_name].find(mongo_query)
            cursor = cursor.sort(sort_by, sort_order)
            cursor = cursor.skip(skip).limit(limit)
            
            documents_data = await cursor.to_list(length=None)
            # Convert ObjectId to string for each document
            for doc in documents_data:
                doc["_id"] = str(doc["_id"])
            documents = [JsonDocument(**doc) for doc in documents_data]
            
            return ServiceResponse.success_response(documents, f"找到会话 {session_id} 的 {len(documents)} 个文档")

        except Exception as e:
            return ServiceResponse.error_response(f"查询会话文档失败: {str(e)}")

    async def get_session_statistics(
        self, 
        project_id: str, 
        session_id: str
    ) -> ServiceResponse[Dict[str, Any]]:
        """Get statistics for a specific session."""
        try:
            pipeline = [
                {"$match": {"project_id": project_id, "session_id": session_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_documents": {"$sum": 1},
                        "total_access_count": {"$sum": "$access_count"},
                        "document_types": {"$push": "$document_type"},
                        "first_created": {"$min": "$created_at"},
                        "last_updated": {"$max": "$updated_at"},
                        "public_documents": {
                            "$sum": {"$cond": [{"$eq": ["$is_public", True]}, 1, 0]}
                        }
                    }
                }
            ]

            result = await self.db[self.collection_name].aggregate(pipeline).to_list(length=None)
            
            if not result:
                return ServiceResponse.success_response({
                    "total_documents": 0,
                    "total_access_count": 0,
                    "public_documents": 0,
                    "private_documents": 0,
                    "type_distribution": {},
                    "first_created": None,
                    "last_updated": None
                }, f"会话 {session_id} 统计信息")

            stats = result[0]
            
            # Calculate type distribution
            type_distribution = {}
            for doc_type in stats.get("document_types", []):
                type_distribution[doc_type] = type_distribution.get(doc_type, 0) + 1

            stats_result = {
                "session_id": session_id,
                "total_documents": stats.get("total_documents", 0),
                "total_access_count": stats.get("total_access_count", 0),
                "public_documents": stats.get("public_documents", 0),
                "private_documents": stats.get("total_documents", 0) - stats.get("public_documents", 0),
                "type_distribution": type_distribution,
                "first_created": stats.get("first_created"),
                "last_updated": stats.get("last_updated")
            }

            return ServiceResponse.success_response(stats_result, f"获取会话 {session_id} 统计信息成功")

        except Exception as e:
            return ServiceResponse.error_response(f"获取会话统计信息失败: {str(e)}")

    async def delete_session_documents(
        self, 
        project_id: str, 
        session_id: str,
        deleted_by: str = "system"
    ) -> ServiceResponse[Dict[str, Any]]:
        """Delete all documents for a specific session."""
        try:
            # Find all documents for the session
            documents_query = {
                "project_id": project_id,
                "session_id": session_id
            }
            
            # Get documents for version tracking
            documents_cursor = self.db[self.collection_name].find(documents_query)
            documents_data = await documents_cursor.to_list(length=None)
            
            if not documents_data:
                return ServiceResponse.success_response({
                    "deleted_count": 0,
                    "session_id": session_id
                }, f"会话 {session_id} 中没有找到文档")

            # Delete all documents for the session
            delete_result = await self.db[self.collection_name].delete_many(documents_query)
            
            result = {
                "deleted_count": delete_result.deleted_count,
                "session_id": session_id,
                "documents_deleted": [str(doc["_id"]) for doc in documents_data]
            }

            return ServiceResponse.success_response(result, f"成功删除会话 {session_id} 的 {delete_result.deleted_count} 个文档")

        except Exception as e:
            return ServiceResponse.error_response(f"删除会话文档失败: {str(e)}")

    # ==================== Batch Operations ====================
    
    async def batch_operation(
        self, 
        project_id: str, 
        batch: JsonDocumentBatch,
        operator: str = "system"
    ) -> ServiceResponse[Dict[str, Any]]:
        """Perform batch operations on multiple documents."""
        try:
            # Validate document IDs
            valid_ids = []
            for doc_id in batch.document_ids:
                if ObjectId.is_valid(doc_id):
                    valid_ids.append(ObjectId(doc_id))
            
            if not valid_ids:
                return ServiceResponse.validation_error("没有有效的文档ID")

            # Build base query
            base_query = {
                "_id": {"$in": valid_ids},
                "project_id": project_id
            }

            operation_results = {"success_count": 0, "error_count": 0, "details": []}

            if batch.operation == "delete":
                # Batch delete
                result = await self.db[self.collection_name].delete_many(base_query)
                operation_results["success_count"] = result.deleted_count
                operation_results["details"].append(f"删除了 {result.deleted_count} 个文档")

            elif batch.operation == "update_tags":
                # Batch update tags
                new_tags = batch.parameters.get("tags", [])
                result = await self.db[self.collection_name].update_many(
                    base_query,
                    {
                        "$set": {
                            "tags": new_tags,
                            "updated_at": datetime.now(),
                            "updated_by": operator
                        }
                    }
                )
                operation_results["success_count"] = result.modified_count
                operation_results["details"].append(f"更新了 {result.modified_count} 个文档的标签")

            elif batch.operation == "update_type":
                # Batch update document type
                new_type = batch.parameters.get("document_type")
                if new_type and new_type in [t.value for t in DocumentType]:
                    result = await self.db[self.collection_name].update_many(
                        base_query,
                        {
                            "$set": {
                                "document_type": new_type,
                                "updated_at": datetime.now(),
                                "updated_by": operator
                            }
                        }
                    )
                    operation_results["success_count"] = result.modified_count
                    operation_results["details"].append(f"更新了 {result.modified_count} 个文档的类型")
                else:
                    return ServiceResponse.validation_error("无效的文档类型")

            elif batch.operation == "set_public":
                # Batch update public status
                is_public = batch.parameters.get("is_public", False)
                result = await self.db[self.collection_name].update_many(
                    base_query,
                    {
                        "$set": {
                            "is_public": is_public,
                            "updated_at": datetime.now(),
                            "updated_by": operator
                        }
                    }
                )
                operation_results["success_count"] = result.modified_count
                operation_results["details"].append(f"更新了 {result.modified_count} 个文档的公开状态")

            else:
                return ServiceResponse.validation_error(f"不支持的批量操作: {batch.operation}")

            return ServiceResponse.success_response(operation_results, "批量操作完成")

        except Exception as e:
            return ServiceResponse.error_response(f"批量操作失败: {str(e)}")

    # ==================== Statistics and Analytics ====================
    
    async def get_document_statistics(self, project_id: str) -> ServiceResponse[Dict[str, Any]]:
        """Get document statistics for a project."""
        try:
            pipeline = [
                {"$match": {"project_id": project_id}},
                {
                    "$group": {
                        "_id": None,
                        "total_documents": {"$sum": 1},
                        "total_access_count": {"$sum": "$access_count"},
                        "public_documents": {
                            "$sum": {"$cond": [{"$eq": ["$is_public", True]}, 1, 0]}
                        },
                        "private_documents": {
                            "$sum": {"$cond": [{"$eq": ["$is_public", False]}, 1, 0]}
                        },
                        "document_types": {"$push": "$document_type"}
                    }
                }
            ]

            result = await self.db[self.collection_name].aggregate(pipeline).to_list(length=None)
            
            if not result:
                return ServiceResponse.success_response({
                    "total_documents": 0,
                    "total_access_count": 0,
                    "public_documents": 0,
                    "private_documents": 0,
                    "type_distribution": {}
                }, "获取统计信息成功")

            stats = result[0]
            
            # Calculate type distribution
            type_distribution = {}
            for doc_type in stats.get("document_types", []):
                type_distribution[doc_type] = type_distribution.get(doc_type, 0) + 1

            stats_result = {
                "total_documents": stats.get("total_documents", 0),
                "total_access_count": stats.get("total_access_count", 0),
                "public_documents": stats.get("public_documents", 0),
                "private_documents": stats.get("private_documents", 0),
                "type_distribution": type_distribution
            }

            return ServiceResponse.success_response(stats_result, "获取统计信息成功")

        except Exception as e:
            return ServiceResponse.error_response(f"获取统计信息失败: {str(e)}")
