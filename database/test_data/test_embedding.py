"""
임베딩 생성 테스트
"""

import json
import time
from embedding_engine import EmbeddingEngine, VectorStore, create_embeddings_pipeline

def test_embedding():
    """임베딩 생성 및 ChromaDB 저장 테스트"""

    print("=== 임베딩 생성 시작 ===")

    # 1. 임베딩 엔진 초기화
    print("1. 임베딩 엔진 초기화...")
    start_time = time.time()
    engine = EmbeddingEngine()
    print(f"   초기화 완료: {time.time() - start_time:.2f}초")

    # 2. 청킹 데이터 로드
    print("2. 청킹 데이터 로드...")
    with open('chunked_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    chunks = data['chunks']
    print(f"   {len(chunks)}개 청크 로드 완료")

    # 3. 테스트 임베딩 생성 (처음 3개만)
    print("3. 테스트 임베딩 생성...")
    test_texts = [chunk['text'] for chunk in chunks[:3]]

    start_time = time.time()
    embeddings = engine.embed_batch(test_texts, show_progress=False)
    print(f"   {len(test_texts)}개 임베딩 생성: {time.time() - start_time:.2f}초")
    print(f"   임베딩 차원: {embeddings.shape}")

    # 4. 전체 임베딩 생성
    print("4. 전체 청크 임베딩 생성...")
    all_texts = [chunk['text'] for chunk in chunks]

    start_time = time.time()
    all_embeddings = engine.embed_batch(all_texts, show_progress=True)
    print(f"   {len(all_texts)}개 임베딩 생성 완료: {time.time() - start_time:.2f}초")

    # 5. 임베딩 저장
    print("5. 임베딩 저장...")
    embedding_map = {
        chunk['chunk_id']: all_embeddings[i]
        for i, chunk in enumerate(chunks)
    }
    embeddings_file = engine.save_embeddings(embedding_map)
    print(f"   저장 완료: {embeddings_file}")

    # 6. ChromaDB 저장
    print("6. ChromaDB 저장...")
    try:
        vector_store = VectorStore(store_type="chromadb")
        vector_store.add_embeddings(chunks, embedding_map)
        print("   ChromaDB 저장 완료")
    except Exception as e:
        print(f"   ChromaDB 저장 실패: {e}")

    # 7. 검색 테스트
    print("7. 검색 테스트...")
    test_query = "지출보고서 작성"
    query_embedding = engine.embed_text(test_query)

    try:
        results = vector_store.search(query_embedding, top_k=3)
        print(f"   '{test_query}' 검색 결과: {len(results)}개")
        for i, result in enumerate(results, 1):
            print(f"   {i}. {result['text'][:50]}...")
    except Exception as e:
        print(f"   검색 실패: {e}")

    print("\n=== 임베딩 생성 완료 ===")
    return engine, vector_store

if __name__ == "__main__":
    test_embedding()