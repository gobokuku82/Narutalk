"""
Vector Service for semantic search
Handles embedding, ChromaDB search, and reranking
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sentence_transformers import SentenceTransformer, CrossEncoder
from services.data_api.repositories.vector_repository import (
    VectorRepository,
    ComplianceSearchRepository,
    HRRulesSearchRepository
)

logger = logging.getLogger(__name__)


class VectorService:
    """Service for vector search operations"""

    def __init__(self):
        """Initialize Vector Service with embedding and reranking models"""
        try:
            # Initialize embedding model (kure-v1)
            model_path = Path(__file__).parent.parent.parent.parent / "models" / "kure_v1"
            self.embedding_model = SentenceTransformer(
                str(model_path),
                device="cpu"  # Use GPU if available: "cuda"
            )

            # Initialize reranker model
            reranker_path = Path(__file__).parent.parent.parent.parent / "models" / "bge-reranker-v2-m3-ko"
            self.reranker = CrossEncoder(
                str(reranker_path),
                max_length=512,
                device="cpu"
            )

            # Initialize repositories
            self.vector_repo = VectorRepository()
            self.compliance_repo = ComplianceSearchRepository()
            self.hr_rules_repo = HRRulesSearchRepository()

            logger.info("Vector Service initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing Vector Service: {e}")
            self.embedding_model = None
            self.reranker = None

    async def search_compliance_rules(
        self,
        query: str,
        activity_type: Optional[str] = None,
        target_type: Optional[str] = None,
        limit_value: Optional[float] = None,
        use_reranker: bool = True,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Search compliance rules with semantic search

        Args:
            query: Search query
            activity_type: Type of activity
            target_type: Target audience type
            limit_value: Maximum allowed amount
            use_reranker: Whether to use reranker
            top_k: Number of results

        Returns:
            Search results with compliance rules
        """
        try:
            # Search using repository
            initial_results = await self.compliance_repo.search_compliance_rules(
                query=query,
                activity_type=activity_type,
                target_type=target_type,
                limit_value=limit_value,
                top_k=top_k * 2 if use_reranker else top_k
            )

            if not initial_results:
                return {
                    "query": query,
                    "results": [],
                    "count": 0
                }

            # Rerank if requested
            if use_reranker and self.reranker:
                reranked_results = self._rerank_results(query, initial_results)
                final_results = reranked_results[:top_k]
            else:
                final_results = initial_results[:top_k]

            # Format response
            formatted_results = []
            for result in final_results:
                formatted_results.append({
                    "text": result["text"],
                    "metadata": result["metadata"],
                    "score": 1 - result.get("distance", 0),  # Convert distance to similarity
                    "law_name": result["metadata"].get("law_name", "Unknown"),
                    "article": result["metadata"].get("article", ""),
                    "prohibition_type": result["metadata"].get("prohibition_type", "")
                })

            return {
                "query": query,
                "filters": {
                    "activity_type": activity_type,
                    "target_type": target_type,
                    "limit_value": limit_value
                },
                "results": formatted_results,
                "count": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Error in compliance search: {e}")
            return {
                "error": str(e),
                "results": []
            }

    async def search_hr_rules(
        self,
        query: str,
        rule_type: Optional[str] = None,
        department: Optional[str] = None,
        use_reranker: bool = True,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Search internal HR rules

        Args:
            query: Search query
            rule_type: Type of rule
            department: Related department
            use_reranker: Whether to use reranker
            top_k: Number of results

        Returns:
            Search results with HR rules
        """
        try:
            # Search using repository
            initial_results = await self.hr_rules_repo.search_hr_rules(
                query=query,
                rule_type=rule_type,
                department=department,
                top_k=top_k * 2 if use_reranker else top_k
            )

            if not initial_results:
                return {
                    "query": query,
                    "results": [],
                    "count": 0
                }

            # Rerank if requested
            if use_reranker and self.reranker:
                reranked_results = self._rerank_results(query, initial_results)
                final_results = reranked_results[:top_k]
            else:
                final_results = initial_results[:top_k]

            # Format response
            formatted_results = []
            for result in final_results:
                formatted_results.append({
                    "text": result["text"],
                    "metadata": result["metadata"],
                    "score": 1 - result.get("distance", 0),
                    "rule_type": result["metadata"].get("rule_type", ""),
                    "part": result["metadata"].get("part", ""),
                    "article": result["metadata"].get("article_num", "")
                })

            return {
                "query": query,
                "filters": {
                    "rule_type": rule_type,
                    "department": department
                },
                "results": formatted_results,
                "count": len(formatted_results)
            }

        except Exception as e:
            logger.error(f"Error in HR rules search: {e}")
            return {
                "error": str(e),
                "results": []
            }

    async def general_vector_search(
        self,
        query: str,
        collection_name: str,
        db_type: str = "rules",
        filters: Optional[Dict] = None,
        use_reranker: bool = False,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        General vector search for any collection

        Args:
            query: Search query
            collection_name: ChromaDB collection name
            db_type: Database type ('rules' or 'hr_rules')
            filters: Metadata filters
            use_reranker: Whether to use reranker
            top_k: Number of results

        Returns:
            Search results
        """
        try:
            # Initialize appropriate repository
            repo = VectorRepository(db_type=db_type)

            # Search
            initial_results = await repo.search_similar(
                query=query,
                collection_name=collection_name,
                top_k=top_k * 2 if use_reranker else top_k,
                filters=filters
            )

            if not initial_results:
                return {
                    "query": query,
                    "results": [],
                    "count": 0
                }

            # Rerank if requested
            if use_reranker and self.reranker:
                reranked_results = self._rerank_results(query, initial_results)
                final_results = reranked_results[:top_k]
            else:
                final_results = initial_results[:top_k]

            return {
                "query": query,
                "collection": collection_name,
                "filters": filters,
                "results": final_results,
                "count": len(final_results)
            }

        except Exception as e:
            logger.error(f"Error in general vector search: {e}")
            return {
                "error": str(e),
                "results": []
            }

    def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results using CrossEncoder

        Args:
            query: Original query
            results: Initial search results

        Returns:
            Reranked results
        """
        try:
            if not results or not self.reranker:
                return results

            # Prepare pairs for reranking
            pairs = [[query, result["text"]] for result in results]

            # Get reranking scores
            scores = self.reranker.predict(pairs)

            # Add scores to results and sort
            for i, result in enumerate(results):
                result["rerank_score"] = float(scores[i])

            # Sort by rerank score
            reranked = sorted(
                results,
                key=lambda x: x.get("rerank_score", 0),
                reverse=True
            )

            return reranked

        except Exception as e:
            logger.error(f"Error in reranking: {e}")
            return results

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        try:
            if not self.embedding_model:
                raise ValueError("Embedding model not initialized")

            embedding = self.embedding_model.encode(
                text,
                normalize_embeddings=True
            )

            return embedding.tolist()

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return []

    async def get_collection_info(
        self,
        collection_name: str,
        db_type: str = "rules"
    ) -> Dict[str, Any]:
        """
        Get information about a vector collection

        Args:
            collection_name: Collection name
            db_type: Database type

        Returns:
            Collection information
        """
        try:
            repo = VectorRepository(db_type=db_type)
            return await repo.get_collection_info(collection_name)

        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return {
                "error": str(e)
            }