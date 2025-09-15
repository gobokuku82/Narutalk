"""
ChromaDB 설정 및 초기화 모듈
좋은제약 내부 규정 벡터 DB 구축
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import json
from pathlib import Path
import sys
import os

class ChromaDBManager:
    """ChromaDB 관리 클래스"""

    def __init__(self, persist_directory: str = "./whanin_chroma_db"):
        """
        Args:
            persist_directory: ChromaDB 저장 경로
        """
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Windows 콘솔 UTF-8 설정
        if sys.platform == 'win32':
            os.system('chcp 65001 > nul 2>&1')
            sys.stdout.reconfigure(encoding='utf-8')

        # ChromaDB 클라이언트 초기화
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        self.collection = None
        self.collection_name = "internal_regulations"

    def create_or_get_collection(self, reset: bool = False) -> chromadb.Collection:
        """컬렉션 생성 또는 가져오기"""
        try:
            if reset:
                # 기존 컬렉션 삭제
                try:
                    self.client.delete_collection(name=self.collection_name)
                    print(f"[INFO] 기존 컬렉션 '{self.collection_name}' 삭제")
                except:
                    pass

            # 컬렉션 생성 또는 가져오기
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "description": "좋은제약 내부 규정 (취업규칙, 인사관리, 복무규정, 윤리강령)",
                    "language": "korean",
                    "embedding_model": "Kure-v1"
                }
            )

            print(f"[OK] 컬렉션 '{self.collection_name}' 준비 완료")
            print(f"    현재 문서 수: {self.collection.count()}")

            return self.collection

        except Exception as e:
            print(f"[ERROR] 컬렉션 생성 실패: {e}")
            raise

    def add_documents(self, chunks: List[Dict], embeddings: Optional[List] = None):
        """문서 추가"""
        if not self.collection:
            self.create_or_get_collection()

        documents = []
        metadatas = []
        ids = []

        for chunk in chunks:
            # 텍스트
            documents.append(chunk['text'])

            # 메타데이터
            metadata = chunk['metadata'].copy()

            # ChromaDB는 문자열, 숫자, 불린만 지원
            # 리스트는 문자열로 변환
            for key, value in metadata.items():
                if isinstance(value, list):
                    metadata[key] = ','.join(str(v) for v in value)
                elif value is None:
                    metadata[key] = ''

            metadatas.append(metadata)

            # ID
            ids.append(chunk['metadata']['chunk_id'])

        try:
            if embeddings:
                # 임베딩과 함께 추가
                self.collection.add(
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    ids=ids
                )
            else:
                # 문서만 추가 (ChromaDB가 자동으로 임베딩 생성)
                self.collection.add(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )

            print(f"[OK] {len(documents)}개 문서 추가 완료")
            print(f"    총 문서 수: {self.collection.count()}")

        except Exception as e:
            print(f"[ERROR] 문서 추가 실패: {e}")
            raise

    def search(self,
              query_text: str = None,
              query_embedding: List[float] = None,
              n_results: int = 5,
              where: Dict = None,
              where_document: Dict = None) -> Dict:
        """검색 수행"""
        if not self.collection:
            raise ValueError("컬렉션이 초기화되지 않았습니다.")

        try:
            if query_embedding:
                # 임베딩으로 검색
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
            elif query_text:
                # 텍스트로 검색
                results = self.collection.query(
                    query_texts=[query_text],
                    n_results=n_results,
                    where=where,
                    where_document=where_document
                )
            else:
                raise ValueError("query_text 또는 query_embedding이 필요합니다.")

            # 결과 포맷팅
            formatted_results = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    result = {
                        'id': results['ids'][0][i],
                        'text': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    }
                    formatted_results.append(result)

            return {
                'results': formatted_results,
                'total': len(formatted_results)
            }

        except Exception as e:
            print(f"[ERROR] 검색 실패: {e}")
            raise

    def search_with_filter(self,
                          query: str,
                          part: str = None,
                          compliance_only: bool = False,
                          importance_min: int = None,
                          n_results: int = 5) -> Dict:
        """필터를 사용한 검색"""
        where_conditions = {}

        if part:
            where_conditions['part'] = part

        if compliance_only:
            where_conditions['compliance_related'] = 'True'  # 문자열로 저장됨

        if importance_min:
            where_conditions['importance_score'] = {'$gte': importance_min}

        return self.search(
            query_text=query,
            n_results=n_results,
            where=where_conditions if where_conditions else None
        )

    def get_statistics(self) -> Dict:
        """DB 통계"""
        if not self.collection:
            return {}

        total_count = self.collection.count()

        # 샘플링으로 메타데이터 분석 (전체가 너무 많을 경우)
        sample_size = min(100, total_count)
        if sample_size > 0:
            sample = self.collection.get(limit=sample_size)

            stats = {
                'total_documents': total_count,
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory),
                'parts': {},
                'chunk_types': {},
                'compliance_related': 0
            }

            # 메타데이터 분석
            for metadata in sample['metadatas']:
                # 부별 통계
                part = metadata.get('part', 'unknown')
                stats['parts'][part] = stats['parts'].get(part, 0) + 1

                # 청크 타입별 통계
                chunk_type = metadata.get('chunk_type', 'unknown')
                stats['chunk_types'][chunk_type] = stats['chunk_types'].get(chunk_type, 0) + 1

                # 준법 관련
                if metadata.get('compliance_related') == 'True':
                    stats['compliance_related'] += 1

            # 비율로 변환 (샘플 기반)
            if sample_size < total_count:
                ratio = total_count / sample_size
                for key in stats['parts']:
                    stats['parts'][key] = int(stats['parts'][key] * ratio)
                for key in stats['chunk_types']:
                    stats['chunk_types'][key] = int(stats['chunk_types'][key] * ratio)
                stats['compliance_related'] = int(stats['compliance_related'] * ratio)

        else:
            stats = {'total_documents': 0}

        return stats

    def delete_collection(self):
        """컬렉션 삭제"""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"[OK] 컬렉션 '{self.collection_name}' 삭제 완료")
            self.collection = None
        except Exception as e:
            print(f"[ERROR] 컬렉션 삭제 실패: {e}")

    def reset_database(self):
        """데이터베이스 초기화"""
        try:
            self.client.reset()
            print("[OK] 데이터베이스 초기화 완료")
            self.collection = None
        except Exception as e:
            print(f"[ERROR] 데이터베이스 초기화 실패: {e}")


def test_chromadb_setup():
    """ChromaDB 설정 테스트"""
    print("="*60)
    print("ChromaDB 설정 테스트")
    print("="*60)

    try:
        # 1. ChromaDB 매니저 초기화
        print("\n1. ChromaDB 초기화...")
        db_manager = ChromaDBManager(persist_directory="./test_chroma_db")

        # 2. 컬렉션 생성
        print("\n2. 컬렉션 생성...")
        collection = db_manager.create_or_get_collection(reset=True)

        # 3. 청크 데이터 로드
        print("\n3. 청크 데이터 로드...")
        chunk_file = Path("chunked_regulations.json")

        if chunk_file.exists():
            with open(chunk_file, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)

            chunks = chunk_data['chunks']
            print(f"   로드된 청크: {len(chunks)}개")

            # 4. 문서 추가 (임베딩 없이 - ChromaDB가 자동 생성)
            print("\n4. 문서 추가 중...")
            db_manager.add_documents(chunks)

            # 5. 검색 테스트
            print("\n5. 검색 테스트...")

            # 일반 검색
            print("\n   5.1 일반 검색: '윤리강령'")
            results = db_manager.search(query_text="윤리강령", n_results=3)
            for i, result in enumerate(results['results'], 1):
                print(f"      [{i}] {result['text'][:80]}...")
                print(f"          부: {result['metadata'].get('part')}")
                print(f"          조항: {result['metadata'].get('article_nums')}")

            # 필터 검색
            print("\n   5.2 필터 검색: 제4부 윤리강령")
            results = db_manager.search_with_filter(
                query="부정청탁",
                part="제4부_윤리강령_CP",
                n_results=3
            )
            print(f"      검색 결과: {results['total']}개")

            # 준법 관련만 검색
            print("\n   5.3 준법 관련 문서 검색")
            results = db_manager.search_with_filter(
                query="규정",
                compliance_only=True,
                n_results=3
            )
            print(f"      검색 결과: {results['total']}개")

            # 6. 통계
            print("\n6. DB 통계:")
            stats = db_manager.get_statistics()
            print(f"   총 문서 수: {stats['total_documents']}")
            print(f"   부별 분포:")
            for part, count in stats.get('parts', {}).items():
                print(f"     - {part}: {count}개")
            print(f"   청크 타입별:")
            for chunk_type, count in stats.get('chunk_types', {}).items():
                print(f"     - {chunk_type}: {count}개")
            print(f"   준법 관련: {stats.get('compliance_related', 0)}개")

        else:
            print("[WARNING] chunked_regulations.json 파일이 없습니다.")
            print("         text_chunker.py를 먼저 실행하세요.")

        print("\n[OK] ChromaDB 설정 테스트 완료!")
        return db_manager

    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_chromadb_setup()