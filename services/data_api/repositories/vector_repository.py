"""
Vector Database Repository
Handles ChromaDB operations for vector search
"""

from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.database import chromadb_conn

logger = logging.getLogger(__name__)


class VectorRepository:
    """Repository for vector database operations"""

    def __init__(self, db_type: str = "rules"):
        """
        Initialize vector repository

        Args:
            db_type: 'rules' for compliance rules, 'hr_rules' for internal rules
        """
        self.db_type = db_type
        self.chromadb = chromadb_conn

    async def search_similar(
        self,
        query: str,
        collection_name: str,
        top_k: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents using vector similarity

        Args:
            query: Search query text
            collection_name: Name of the ChromaDB collection
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of similar documents with scores
        """
        try:
            collection = self.chromadb.get_collection(self.db_type, collection_name)
            if not collection:
                logger.error(f"Collection {collection_name} not found")
                return []

            # Perform similarity search
            results = collection.query(
                query_texts=[query],
                n_results=top_k,
                where=filters if filters else None
            )

            # Format results
            formatted_results = []
            if results and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        "id": results['ids'][0][i],
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results['distances'] else 0
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []

    async def search_by_metadata(
        self,
        collection_name: str,
        filters: Dict,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search documents by metadata filters

        Args:
            collection_name: Name of the ChromaDB collection
            filters: Metadata filters
            limit: Maximum number of results

        Returns:
            List of matching documents
        """
        try:
            collection = self.chromadb.get_collection(self.db_type, collection_name)
            if not collection:
                logger.error(f"Collection {collection_name} not found")
                return []

            # Get all documents matching filters
            results = collection.get(
                where=filters,
                limit=limit
            )

            # Format results
            formatted_results = []
            if results and results['ids']:
                for i in range(len(results['ids'])):
                    formatted_results.append({
                        "id": results['ids'][i],
                        "text": results['documents'][i] if results['documents'] else "",
                        "metadata": results['metadatas'][i] if results['metadatas'] else {}
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error in metadata search: {e}")
            return []

    async def get_document_by_id(
        self,
        collection_name: str,
        doc_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific document by ID

        Args:
            collection_name: Name of the ChromaDB collection
            doc_id: Document ID

        Returns:
            Document data or None
        """
        try:
            collection = self.chromadb.get_collection(self.db_type, collection_name)
            if not collection:
                logger.error(f"Collection {collection_name} not found")
                return None

            results = collection.get(ids=[doc_id])

            if results and results['ids']:
                return {
                    "id": results['ids'][0],
                    "text": results['documents'][0] if results['documents'] else "",
                    "metadata": results['metadatas'][0] if results['metadatas'] else {}
                }

            return None

        except Exception as e:
            logger.error(f"Error getting document by ID: {e}")
            return None

    async def hybrid_search(
        self,
        query: str,
        collection_name: str,
        text_filters: Optional[Dict] = None,
        metadata_filters: Optional[Dict] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and metadata filters

        Args:
            query: Search query text
            collection_name: Name of the ChromaDB collection
            text_filters: Filters for text content
            metadata_filters: Filters for metadata
            top_k: Number of results to return

        Returns:
            List of search results
        """
        try:
            # Combine filters
            combined_filters = {}
            if metadata_filters:
                combined_filters.update(metadata_filters)

            # Perform vector search with filters
            results = await self.search_similar(
                query=query,
                collection_name=collection_name,
                top_k=top_k * 2,  # Get more results for filtering
                filters=combined_filters if combined_filters else None
            )

            # Additional text filtering if needed
            if text_filters and results:
                filtered_results = []
                for result in results:
                    text = result.get("text", "").lower()
                    match = True

                    for key, value in text_filters.items():
                        if key == "contains" and value.lower() not in text:
                            match = False
                            break
                        elif key == "not_contains" and value.lower() in text:
                            match = False
                            break

                    if match:
                        filtered_results.append(result)

                results = filtered_results

            return results[:top_k]

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return []

    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get information about a collection

        Args:
            collection_name: Name of the ChromaDB collection

        Returns:
            Collection information
        """
        try:
            collection = self.chromadb.get_collection(self.db_type, collection_name)
            if not collection:
                return {"error": f"Collection {collection_name} not found"}

            # Get collection count
            count = collection.count()

            # Get sample documents
            sample = collection.peek(3)

            return {
                "name": collection_name,
                "count": count,
                "sample_documents": [
                    {
                        "id": sample['ids'][i] if i < len(sample['ids']) else None,
                        "text": sample['documents'][i][:200] + "..." if i < len(sample['documents']) else None,
                        "metadata": sample['metadatas'][i] if sample['metadatas'] and i < len(sample['metadatas']) else {}
                    }
                    for i in range(min(3, len(sample['ids']) if sample['ids'] else 0))
                ]
            }

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {"error": str(e)}


# Specialized repositories for specific use cases

class ComplianceSearchRepository(VectorRepository):
    """Specialized repository for compliance rule searches"""

    def __init__(self):
        super().__init__(db_type="rules")
        self.collection_name = "compliance_rules"

    async def search_compliance_rules(
        self,
        query: str,
        activity_type: Optional[str] = None,
        target_type: Optional[str] = None,
        limit_value: Optional[float] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search compliance rules with specific filters

        Args:
            query: Search query
            activity_type: Type of activity (e.g., "제품설명회", "학술대회")
            target_type: Target type (e.g., "의료인", "공직자")
            limit_value: Maximum allowed value
            top_k: Number of results

        Returns:
            List of compliance rules
        """
        filters = {}
        if activity_type:
            filters["activity"] = activity_type
        if target_type:
            filters["target"] = target_type
        if limit_value is not None:
            filters["limit_value"] = {"$lte": limit_value}

        return await self.search_similar(
            query=query,
            collection_name=self.collection_name,
            top_k=top_k,
            filters=filters if filters else None
        )


class HRRulesSearchRepository(VectorRepository):
    """Specialized repository for internal HR rule searches"""

    def __init__(self):
        super().__init__(db_type="hr_rules")
        self.collection_name = "internal_regulations"

    async def search_hr_rules(
        self,
        query: str,
        rule_type: Optional[str] = None,
        department: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search internal HR rules

        Args:
            query: Search query
            rule_type: Type of rule (e.g., "윤리", "인사", "복무")
            department: Related department
            top_k: Number of results

        Returns:
            List of HR rules
        """
        filters = {}
        if rule_type:
            filters["rule_type"] = rule_type
        if department:
            filters["department"] = department

        return await self.search_similar(
            query=query,
            collection_name=self.collection_name,
            top_k=top_k,
            filters=filters if filters else None
        )