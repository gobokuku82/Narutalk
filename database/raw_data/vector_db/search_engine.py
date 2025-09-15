"""
검색 엔진 - 시맨틱 검색, 동의어 처리, 리랭킹
"""

import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys
import os

class SearchEngine:
    """벡터 검색 엔진"""

    def __init__(self, chroma_manager=None, embedding_processor=None):
        """
        Args:
            chroma_manager: ChromaDB 매니저 인스턴스
            embedding_processor: 임베딩 프로세서 인스턴스
        """
        # Windows 콘솔 UTF-8 설정
        if sys.platform == 'win32':
            os.system('chcp 65001 > nul 2>&1')
            sys.stdout.reconfigure(encoding='utf-8')

        self.chroma_manager = chroma_manager
        self.embedding_processor = embedding_processor

        # 동의어 사전
        self.synonym_dict = {
            "직원": ["근로자", "임직원", "사원", "종업원"],
            "CP": ["공정거래", "자율준수프로그램", "Compliance Program", "컴플라이언스"],
            "윤리": ["윤리강령", "윤리규정", "행동강령", "윤리규범"],
            "징계": ["제재", "처벌", "불이익", "징벌"],
            "휴가": ["휴일", "연차", "휴직", "연가"],
            "평가": ["평정", "심사", "고과", "인사평가"],
            "채용": ["고용", "입사", "취업", "신규채용"],
            "퇴직": ["퇴사", "사직", "이직", "해고"],
            "급여": ["임금", "급료", "보수", "월급"],
            "승진": ["진급", "승급", "직급상승"]
        }

        # 역방향 매핑 생성
        self.reverse_synonyms = {}
        for main_term, synonyms in self.synonym_dict.items():
            for synonym in synonyms:
                self.reverse_synonyms[synonym.lower()] = main_term

    def expand_query(self, query: str) -> str:
        """쿼리 확장 (동의어 추가)"""
        expanded_terms = [query]
        query_lower = query.lower()

        # 동의어 확장
        for term, synonyms in self.synonym_dict.items():
            if term.lower() in query_lower:
                expanded_terms.extend(synonyms[:2])  # 상위 2개만

        # 역방향 확인
        words = query.split()
        for word in words:
            word_lower = word.lower()
            if word_lower in self.reverse_synonyms:
                main_term = self.reverse_synonyms[word_lower]
                if main_term not in expanded_terms:
                    expanded_terms.append(main_term)

        expanded_query = ' '.join(expanded_terms[:5])  # 최대 5개 용어
        return expanded_query

    def search(self,
              query: str,
              top_k: int = 5,
              use_expansion: bool = True,
              filters: Dict = None) -> List[Dict]:
        """시맨틱 검색 수행"""
        if not self.chroma_manager or not self.embedding_processor:
            raise ValueError("ChromaDB 매니저와 임베딩 프로세서가 필요합니다.")

        # 쿼리 확장
        if use_expansion:
            expanded_query = self.expand_query(query)
            print(f"[INFO] 쿼리 확장: '{query}' → '{expanded_query}'")
        else:
            expanded_query = query

        # 쿼리 임베딩 생성
        query_embedding = self.embedding_processor.create_embedding(expanded_query)

        # ChromaDB 검색
        results = self.chroma_manager.search(
            query_embedding=query_embedding.tolist(),
            n_results=top_k * 2,  # 리랭킹을 위해 더 많이 가져옴
            where=filters
        )

        # 리랭킹
        ranked_results = self.rerank_results(
            query=query,
            results=results['results'],
            top_k=top_k
        )

        return ranked_results

    def rerank_results(self,
                       query: str,
                       results: List[Dict],
                       top_k: int) -> List[Dict]:
        """검색 결과 리랭킹"""
        if not results:
            return []

        query_lower = query.lower()

        for result in results:
            score = 0.0

            # 1. 거리 기반 점수 (0~1, 낮을수록 좋음)
            distance = result.get('distance', 1.0)
            distance_score = 1.0 / (1.0 + distance)
            score += distance_score * 0.5

            # 2. 키워드 매칭 점수
            text_lower = result['text'].lower()
            if query_lower in text_lower:
                score += 0.3

            # 3. 메타데이터 점수
            metadata = result.get('metadata', {})

            # 중요도 점수
            importance = int(metadata.get('importance_score', 3))
            score += (importance / 5.0) * 0.1

            # 준법 관련 보너스
            if metadata.get('compliance_related') == 'True':
                score += 0.1

            # 4. 조항 번호 매칭
            article_nums = metadata.get('article_nums', '')
            if article_nums and any(num in query for num in article_nums.split(',')):
                score += 0.2

            result['rerank_score'] = score

        # 점수 기준으로 정렬
        ranked = sorted(results, key=lambda x: x['rerank_score'], reverse=True)

        return ranked[:top_k]

    def search_by_article(self, article_num: str, top_k: int = 3) -> List[Dict]:
        """조항 번호로 검색"""
        # 제N조 형식 정규화
        if not article_num.startswith('제'):
            article_num = f"제{article_num}조"
        elif not article_num.endswith('조'):
            article_num += '조'

        # 메타데이터 필터로 검색
        filters = {
            'article_nums': {'$contains': article_num}
        }

        return self.search(
            query=article_num,
            top_k=top_k,
            use_expansion=False,
            filters=filters
        )

    def search_by_part(self, part: str, query: str = "", top_k: int = 5) -> List[Dict]:
        """부별 검색"""
        part_map = {
            "1": "제1부_취업규칙",
            "2": "제2부_인사관리규정",
            "3": "제3부_복무규정",
            "4": "제4부_윤리강령_CP",
            "취업": "제1부_취업규칙",
            "인사": "제2부_인사관리규정",
            "복무": "제3부_복무규정",
            "윤리": "제4부_윤리강령_CP"
        }

        # 부 이름 정규화
        if part in part_map:
            part = part_map[part]

        filters = {'part': part}

        if query:
            return self.search(query=query, top_k=top_k, filters=filters)
        else:
            # 쿼리 없이 해당 부의 문서만 가져오기
            results = self.chroma_manager.search_with_filter(
                query="규정",
                part=part,
                n_results=top_k
            )
            return results['results']

    def search_compliance(self, query: str = "", top_k: int = 5) -> List[Dict]:
        """준법/윤리 관련 문서만 검색"""
        if not query:
            query = "윤리 준법 CP"

        return self.search(
            query=query,
            top_k=top_k,
            filters={'compliance_related': 'True'}
        )

    def get_context_window(self, chunk_id: str, window_size: int = 1) -> List[Dict]:
        """청크 주변 컨텍스트 가져오기"""
        # 청크 번호 추출
        chunk_num = int(chunk_id.split('_')[1])

        context_ids = []
        for i in range(-window_size, window_size + 1):
            context_num = chunk_num + i
            if context_num >= 0:
                context_ids.append(f"chunk_{context_num:04d}")

        # ChromaDB에서 가져오기
        results = []
        for cid in context_ids:
            try:
                result = self.chroma_manager.collection.get(ids=[cid])
                if result['documents'][0]:
                    results.append({
                        'id': cid,
                        'text': result['documents'][0],
                        'metadata': result['metadatas'][0]
                    })
            except:
                continue

        return results


def test_search_engine():
    """검색 엔진 테스트"""
    print("="*60)
    print("검색 엔진 테스트")
    print("="*60)

    try:
        # 1. 필요한 모듈 임포트
        from chroma_setup import ChromaDBManager
        from embedding_processor import EmbeddingProcessor

        # 2. 컴포넌트 초기화
        print("\n1. 컴포넌트 초기화...")
        chroma_manager = ChromaDBManager(persist_directory="./test_chroma_db")
        chroma_manager.create_or_get_collection()

        embedding_processor = EmbeddingProcessor(model_type="local")

        # 3. 검색 엔진 초기화
        print("\n2. 검색 엔진 초기화...")
        search_engine = SearchEngine(
            chroma_manager=chroma_manager,
            embedding_processor=embedding_processor
        )

        # 데이터가 없으면 먼저 추가
        if chroma_manager.collection.count() == 0:
            print("\n[INFO] 데이터 추가 중...")
            chunk_file = Path("chunked_regulations.json")
            if chunk_file.exists():
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunk_data = json.load(f)
                chunks = chunk_data['chunks']

                # 임베딩 생성
                _, embeddings = embedding_processor.process_chunks(chunks)

                # ChromaDB에 추가
                chroma_manager.add_documents(chunks, embeddings)

        # 4. 일반 검색 테스트
        print("\n3. 일반 검색 테스트...")
        test_queries = ["윤리강령", "휴가", "징계", "채용 절차"]

        for query in test_queries:
            print(f"\n   쿼리: '{query}'")
            results = search_engine.search(query, top_k=3)

            for i, result in enumerate(results, 1):
                print(f"   [{i}] (점수: {result.get('rerank_score', 0):.3f})")
                print(f"       {result['text'][:100]}...")
                print(f"       부: {result['metadata'].get('part', 'N/A')}")

        # 5. 조항 검색 테스트
        print("\n4. 조항 검색 테스트...")
        article_results = search_engine.search_by_article("7", top_k=2)
        print(f"   제7조 검색 결과: {len(article_results)}개")

        # 6. 부별 검색 테스트
        print("\n5. 부별 검색 테스트...")
        part_results = search_engine.search_by_part("윤리", "부정청탁", top_k=3)
        print(f"   윤리 부문 '부정청탁' 검색 결과: {len(part_results)}개")

        # 7. 준법 관련 검색
        print("\n6. 준법 관련 문서 검색...")
        compliance_results = search_engine.search_compliance(top_k=3)
        print(f"   준법 관련 문서: {len(compliance_results)}개")

        # 8. 쿼리 확장 테스트
        print("\n7. 쿼리 확장 테스트...")
        test_terms = ["직원", "CP", "급여"]
        for term in test_terms:
            expanded = search_engine.expand_query(term)
            print(f"   '{term}' → '{expanded}'")

        print("\n[OK] 검색 엔진 테스트 완료!")
        return search_engine

    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_search_engine()