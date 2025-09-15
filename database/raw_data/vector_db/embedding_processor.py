"""
임베딩 프로세서 - Kure-v1 모델을 사용한 한국어 임베딩 생성
OpenAI API 또는 로컬 임베딩 모델 사용
"""

import json
import numpy as np
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import sys
import os
from tqdm import tqdm

# 임베딩 모델 옵션
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("[WARNING] sentence_transformers 설치되지 않음. OpenAI 임베딩 사용")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("[WARNING] openai 설치되지 않음. 로컬 임베딩 사용")


class EmbeddingProcessor:
    """임베딩 생성 및 관리"""

    def __init__(self, model_type: str = "local", model_name: str = None):
        """
        Args:
            model_type: "local" 또는 "openai"
            model_name: 사용할 모델명
        """
        # Windows 콘솔 UTF-8 설정
        if sys.platform == 'win32':
            os.system('chcp 65001 > nul 2>&1')
            sys.stdout.reconfigure(encoding='utf-8')

        self.model_type = model_type
        self.model = None
        self.embeddings_cache = {}

        if model_type == "local" and SENTENCE_TRANSFORMERS_AVAILABLE:
            # 한국어 임베딩 모델 사용
            if model_name is None:
                # 기본 한국어 모델
                model_name = "jhgan/ko-sroberta-multitask"

            try:
                print(f"[INFO] 로컬 모델 로드 중: {model_name}")
                self.model = SentenceTransformer(model_name)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                print(f"[OK] 모델 로드 완료 (차원: {self.embedding_dim})")
            except Exception as e:
                print(f"[ERROR] 모델 로드 실패: {e}")
                self.model_type = "dummy"

        elif model_type == "openai" and OPENAI_AVAILABLE:
            # OpenAI 임베딩 사용
            self.model_name = model_name or "text-embedding-ada-002"
            self.embedding_dim = 1536  # ada-002 차원
            print(f"[INFO] OpenAI 임베딩 모델 사용: {self.model_name}")

            # API 키 확인
            if not openai.api_key:
                print("[WARNING] OpenAI API 키가 설정되지 않았습니다.")
                self.model_type = "dummy"

        else:
            # 더미 임베딩 (테스트용)
            print("[WARNING] 더미 임베딩 모드 (테스트용)")
            self.model_type = "dummy"
            self.embedding_dim = 768

    def create_embedding(self, text: str) -> np.ndarray:
        """단일 텍스트 임베딩 생성"""
        # 캐시 확인
        if text in self.embeddings_cache:
            return self.embeddings_cache[text]

        if self.model_type == "local" and self.model:
            # 로컬 모델 사용
            embedding = self.model.encode(text, convert_to_numpy=True)

        elif self.model_type == "openai" and OPENAI_AVAILABLE:
            # OpenAI API 사용
            try:
                response = openai.Embedding.create(
                    model=self.model_name,
                    input=text
                )
                embedding = np.array(response['data'][0]['embedding'])
            except Exception as e:
                print(f"[ERROR] OpenAI 임베딩 생성 실패: {e}")
                embedding = self._create_dummy_embedding()

        else:
            # 더미 임베딩
            embedding = self._create_dummy_embedding()

        # 캐시에 저장
        self.embeddings_cache[text] = embedding
        return embedding

    def create_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """배치 임베딩 생성"""
        embeddings = []

        if self.model_type == "local" and self.model:
            # 로컬 모델 배치 처리
            print(f"[INFO] {len(texts)}개 텍스트 임베딩 생성 중...")

            for i in tqdm(range(0, len(texts), batch_size), desc="임베딩 생성"):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.model.encode(batch, convert_to_numpy=True)

                if len(batch) == 1:
                    embeddings.append(batch_embeddings)
                else:
                    embeddings.extend(batch_embeddings)

        elif self.model_type == "openai" and OPENAI_AVAILABLE:
            # OpenAI API 배치 처리
            print(f"[INFO] OpenAI API로 {len(texts)}개 임베딩 생성 중...")

            for i in tqdm(range(0, len(texts), batch_size), desc="임베딩 생성"):
                batch = texts[i:i + batch_size]
                try:
                    response = openai.Embedding.create(
                        model=self.model_name,
                        input=batch
                    )
                    batch_embeddings = [np.array(data['embedding'])
                                       for data in response['data']]
                    embeddings.extend(batch_embeddings)
                except Exception as e:
                    print(f"[ERROR] 배치 {i//batch_size} 실패: {e}")
                    # 실패한 배치는 더미로 대체
                    for _ in batch:
                        embeddings.append(self._create_dummy_embedding())

        else:
            # 더미 임베딩
            print(f"[INFO] 더미 임베딩 {len(texts)}개 생성 중...")
            for _ in texts:
                embeddings.append(self._create_dummy_embedding())

        return embeddings

    def _create_dummy_embedding(self) -> np.ndarray:
        """더미 임베딩 생성 (테스트용)"""
        # 랜덤하지만 일관된 더미 임베딩
        np.random.seed(42)
        return np.random.randn(self.embedding_dim).astype(np.float32)

    def process_chunks(self, chunks: List[Dict]) -> Tuple[List[Dict], List[np.ndarray]]:
        """청크 리스트에 대한 임베딩 생성"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.create_embeddings_batch(texts)

        # 청크에 임베딩 차원 정보 추가
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding_dim'] = len(embedding)

        return chunks, embeddings

    def save_embeddings(self, chunks: List[Dict], embeddings: List[np.ndarray],
                       output_path: str = "embeddings.npz"):
        """임베딩 저장"""
        output_path = Path(output_path)

        # NumPy 배열로 저장
        embeddings_array = np.array(embeddings)
        chunk_ids = [chunk['metadata']['chunk_id'] for chunk in chunks]

        np.savez_compressed(
            output_path,
            embeddings=embeddings_array,
            chunk_ids=chunk_ids
        )

        print(f"[OK] 임베딩 저장 완료: {output_path}")
        print(f"    Shape: {embeddings_array.shape}")
        print(f"    크기: {output_path.stat().st_size / 1024 / 1024:.2f} MB")

        return output_path

    def load_embeddings(self, file_path: str) -> Tuple[List[str], np.ndarray]:
        """저장된 임베딩 로드"""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"임베딩 파일을 찾을 수 없습니다: {file_path}")

        data = np.load(file_path)
        chunk_ids = data['chunk_ids'].tolist()
        embeddings = data['embeddings']

        print(f"[OK] 임베딩 로드 완료: {file_path}")
        print(f"    청크 수: {len(chunk_ids)}")
        print(f"    임베딩 차원: {embeddings.shape[1]}")

        return chunk_ids, embeddings

    def calculate_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """코사인 유사도 계산"""
        # 정규화
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # 코사인 유사도
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)


def test_embedding_processor():
    """임베딩 프로세서 테스트"""
    print("="*60)
    print("임베딩 프로세서 테스트")
    print("="*60)

    try:
        # 1. 프로세서 초기화
        print("\n1. 임베딩 프로세서 초기화...")
        processor = EmbeddingProcessor(model_type="local")

        # 2. 청크 데이터 로드
        print("\n2. 청크 데이터 로드...")
        chunk_file = Path("chunked_regulations.json")

        if not chunk_file.exists():
            print("[ERROR] chunked_regulations.json 파일이 없습니다.")
            return None

        with open(chunk_file, 'r', encoding='utf-8') as f:
            chunk_data = json.load(f)

        chunks = chunk_data['chunks']
        print(f"   로드된 청크: {len(chunks)}개")

        # 3. 샘플 임베딩 생성
        print("\n3. 샘플 임베딩 테스트...")
        sample_text = chunks[0]['text'][:200]
        sample_embedding = processor.create_embedding(sample_text)
        print(f"   임베딩 차원: {len(sample_embedding)}")
        print(f"   임베딩 타입: {type(sample_embedding)}")
        print(f"   임베딩 샘플: {sample_embedding[:5]}...")

        # 4. 배치 임베딩 생성 (처음 5개만 테스트)
        print("\n4. 배치 임베딩 생성 (5개)...")
        test_chunks = chunks[:5]
        processed_chunks, embeddings = processor.process_chunks(test_chunks)
        print(f"   생성된 임베딩: {len(embeddings)}개")

        # 5. 유사도 계산 테스트
        print("\n5. 유사도 계산 테스트...")
        if len(embeddings) >= 2:
            sim_same = processor.calculate_similarity(embeddings[0], embeddings[0])
            sim_diff = processor.calculate_similarity(embeddings[0], embeddings[1])
            print(f"   자기 자신과의 유사도: {sim_same:.4f}")
            print(f"   다른 청크와의 유사도: {sim_diff:.4f}")

        # 6. 전체 임베딩 생성
        print("\n6. 전체 청크 임베딩 생성...")
        print(f"   전체 {len(chunks)}개 청크 처리 중...")
        all_chunks, all_embeddings = processor.process_chunks(chunks)
        print(f"   완료: {len(all_embeddings)}개 임베딩 생성")

        # 7. 임베딩 저장
        print("\n7. 임베딩 저장...")
        embedding_file = processor.save_embeddings(
            all_chunks, all_embeddings,
            "regulation_embeddings.npz"
        )

        # 8. 임베딩 로드 테스트
        print("\n8. 임베딩 로드 테스트...")
        loaded_ids, loaded_embeddings = processor.load_embeddings(embedding_file)
        print(f"   로드 확인: {len(loaded_ids)}개 청크")

        print("\n[OK] 임베딩 프로세서 테스트 완료!")
        return processor, all_embeddings

    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    test_embedding_processor()