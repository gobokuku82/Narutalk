"""
텍스트 청킹 모듈 - plan.md 지시사항에 따른 조항 단위 청킹
250-350 토큰 크기 유지 및 메타데이터 생성
"""

import re
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import tiktoken

class TextChunker:
    """텍스트 청킹 및 메타데이터 생성"""

    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        """
        Args:
            model_name: 토큰 카운팅용 모델 (기본값: gpt-3.5-turbo)
        """
        self.tokenizer = tiktoken.encoding_for_model(model_name)
        self.chunks = []
        self.metadata_template = {
            'doc_id': '좋은제약_내부규정',
            'part': None,
            'part_title': None,
            'chapter': None,
            'chapter_title': None,
            'article_nums': [],
            'article_titles': [],
            'chunk_id': None,
            'chunk_sequence': 0,
            'keywords': [],
            'topics': [],
            'compliance_related': False,
            'importance_score': 3,
            'chunk_type': 'regulation',
            'has_subclauses': False,
            'related_articles': [],
            'cross_references': []
        }

        # 부별 청킹 전략
        self.chunking_strategy = {
            '제1부_취업규칙': {
                'chunk_unit': '1-2개 조항',
                'target_tokens': (250, 350),
                'importance': 3
            },
            '제2부_인사관리규정': {
                'chunk_unit': '조항 + 설명문',
                'target_tokens': (300, 400),
                'importance': 4
            },
            '제3부_복무규정': {
                'chunk_unit': '의무사항별 그룹화',
                'target_tokens': (250, 350),
                'importance': 4
            },
            '제4부_윤리강령_CP': {
                'chunk_unit': '핵심 주제별',
                'target_tokens': (300, 450),
                'importance': 5
            }
        }

        # 키워드 사전
        self.keyword_dict = {
            '윤리': ['윤리강령', '윤리규정', '행동강령', 'CP', '준법'],
            '인사': ['채용', '평가', '승진', '보상', '직급'],
            '복무': ['근무', '출퇴근', '의무', '금지사항'],
            '보안': ['비밀유지', '정보보호', '자산보호']
        }

    def count_tokens(self, text: str) -> int:
        """텍스트의 토큰 수 계산"""
        return len(self.tokenizer.encode(text))

    def extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        keywords = []
        text_lower = text.lower()

        for category, words in self.keyword_dict.items():
            for word in words:
                if word.lower() in text_lower:
                    keywords.append(word)

        # 조항 번호 추출
        article_pattern = r'제(\d+)조'
        articles = re.findall(article_pattern, text)
        for article_num in articles:
            keywords.append(f"제{article_num}조")

        return list(set(keywords))

    def determine_topics(self, text: str, part: str) -> List[str]:
        """텍스트의 주제 분류"""
        topics = []

        if '윤리' in text or 'CP' in text or '준법' in text:
            topics.append('윤리')

        if '채용' in text or '평가' in text or '승진' in text:
            topics.append('인사')

        if '근무' in text or '의무' in text or '금지' in text:
            topics.append('복무')

        if '비밀' in text or '보안' in text or '정보보호' in text:
            topics.append('보안')

        # 부에 따른 기본 토픽
        if '제1부' in part:
            topics.append('취업규칙')
        elif '제2부' in part:
            topics.append('인사관리')
        elif '제3부' in part:
            topics.append('복무규정')
        elif '제4부' in part:
            topics.extend(['윤리', 'CP'])

        return list(set(topics))

    def is_compliance_related(self, text: str) -> bool:
        """준법/윤리 관련 여부 확인"""
        compliance_keywords = [
            '윤리', 'CP', '준법', '공정거래', '자율준수',
            '부정청탁', '금품', '이해충돌', '제보', '신고',
            'ISO37001', '반부패', '컴플라이언스'
        ]

        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in compliance_keywords)

    def chunk_by_articles(self, paragraphs: List[Dict]) -> List[Dict]:
        """조항 단위로 청킹"""
        chunks = []
        current_chunk = {
            'text': '',
            'paragraphs': [],
            'metadata': None
        }

        current_part = None
        current_chapter = None
        chunk_sequence = 0

        for para in paragraphs:
            # 부/장 정보 업데이트
            if para['type'] == 'part_header':
                current_part = para['part']
                continue
            elif para['type'] == 'chapter_header':
                current_chapter = para['chapter']
                continue

            # 새로운 조항 시작
            if para['type'] == 'article' and para['article']:
                # 이전 청크 저장
                if current_chunk['text']:
                    token_count = self.count_tokens(current_chunk['text'])

                    # 토큰 수가 너무 적으면 다음 조항과 합치기
                    if token_count < 200:
                        # 계속 현재 청크에 추가
                        current_chunk['text'] += '\n\n' + para['text']
                        current_chunk['paragraphs'].append(para)
                    else:
                        # 청크 완성 및 저장
                        self._finalize_chunk(current_chunk, current_part, current_chapter, chunk_sequence)
                        chunks.append(current_chunk)
                        chunk_sequence += 1

                        # 새 청크 시작
                        current_chunk = {
                            'text': para['text'],
                            'paragraphs': [para],
                            'metadata': None
                        }
                else:
                    # 첫 청크
                    current_chunk['text'] = para['text']
                    current_chunk['paragraphs'].append(para)

            else:
                # 조항이 아닌 텍스트는 현재 청크에 추가
                if current_chunk['text']:
                    current_chunk['text'] += '\n' + para['text']
                    current_chunk['paragraphs'].append(para)

            # 토큰 수 확인 및 청크 분할
            token_count = self.count_tokens(current_chunk['text'])
            if token_count > 400:  # 최대 토큰 수 초과
                self._finalize_chunk(current_chunk, current_part, current_chapter, chunk_sequence)
                chunks.append(current_chunk)
                chunk_sequence += 1

                # 새 청크 시작
                current_chunk = {
                    'text': '',
                    'paragraphs': [],
                    'metadata': None
                }

        # 마지막 청크 저장
        if current_chunk['text']:
            self._finalize_chunk(current_chunk, current_part, current_chapter, chunk_sequence)
            chunks.append(current_chunk)

        return chunks

    def _finalize_chunk(self, chunk: Dict, part: str, chapter: str, sequence: int):
        """청크 메타데이터 완성"""
        metadata = self.metadata_template.copy()

        # 기본 메타데이터
        metadata['part'] = part
        metadata['chapter'] = chapter
        metadata['chunk_sequence'] = sequence
        metadata['chunk_id'] = f"chunk_{sequence:04d}"

        # 조항 정보 추출
        article_nums = []
        article_titles = []

        for para in chunk['paragraphs']:
            if para.get('article'):
                article_nums.append(para['article'])
                if para.get('article_title'):
                    article_titles.append(para['article_title'])

        metadata['article_nums'] = article_nums
        metadata['article_titles'] = article_titles

        # 키워드 및 토픽
        metadata['keywords'] = self.extract_keywords(chunk['text'])
        metadata['topics'] = self.determine_topics(chunk['text'], part or '')

        # 준법 관련 여부
        metadata['compliance_related'] = self.is_compliance_related(chunk['text'])

        # 중요도 설정
        if part and part in self.chunking_strategy:
            metadata['importance_score'] = self.chunking_strategy[part]['importance']

        if metadata['compliance_related']:
            metadata['importance_score'] = min(5, metadata['importance_score'] + 1)

        # 청크 타입 결정
        if any('표' in para.get('text', '') for para in chunk['paragraphs']):
            metadata['chunk_type'] = 'table'
        elif '정의' in chunk['text'] or '용어' in chunk['text']:
            metadata['chunk_type'] = 'definition'
        elif '절차' in chunk['text'] or '프로세스' in chunk['text']:
            metadata['chunk_type'] = 'procedure'
        else:
            metadata['chunk_type'] = 'regulation'

        # 하위 조항 여부
        metadata['has_subclauses'] = any('①' in para.get('text', '') for para in chunk['paragraphs'])

        chunk['metadata'] = metadata

    def chunk_tables(self, tables: List[Dict]) -> List[Dict]:
        """표 데이터 청킹"""
        table_chunks = []

        for i, table in enumerate(tables):
            chunk = {
                'text': table['text_representation'],
                'metadata': self.metadata_template.copy()
            }

            # 표 전용 메타데이터
            chunk['metadata']['chunk_type'] = 'table'
            chunk['metadata']['chunk_id'] = f"table_{i:03d}"
            chunk['metadata']['keywords'] = self.extract_keywords(chunk['text'])
            chunk['metadata']['importance_score'] = 4  # 표는 보통 중요

            # 직급체계 표인지 확인
            if '직급' in chunk['text'] or '직위' in chunk['text']:
                chunk['metadata']['topics'] = ['인사', '직급체계']
                chunk['metadata']['part'] = '제2부_인사관리규정'

            table_chunks.append(chunk)

        return table_chunks

    def process_document(self, structured_content: Dict) -> List[Dict]:
        """문서 전체 처리"""
        all_chunks = []

        # 부별로 처리
        for part_name in ['제1부_취업규칙', '제2부_인사관리규정', '제3부_복무규정', '제4부_윤리강령_CP']:
            if part_name in structured_content:
                part_content = structured_content[part_name]
                if part_content:
                    part_chunks = self.chunk_by_articles(part_content)
                    all_chunks.extend(part_chunks)

        # 표 처리
        if 'tables' in structured_content:
            table_chunks = self.chunk_tables(structured_content['tables'])
            all_chunks.extend(table_chunks)

        # 청크 ID 재정렬
        for i, chunk in enumerate(all_chunks):
            if chunk.get('metadata'):
                chunk['metadata']['chunk_sequence'] = i
                chunk['metadata']['chunk_id'] = f"chunk_{i:04d}"

        self.chunks = all_chunks
        return all_chunks

    def save_chunks(self, output_path: str = 'chunked_data.json'):
        """청크 데이터 저장"""
        output_path = Path(output_path)

        chunk_data = {
            'total_chunks': len(self.chunks),
            'chunks': []
        }

        for chunk in self.chunks:
            chunk_item = {
                'chunk_id': chunk['metadata']['chunk_id'],
                'text': chunk['text'],
                'metadata': chunk['metadata'],
                'token_count': self.count_tokens(chunk['text'])
            }
            chunk_data['chunks'].append(chunk_item)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=2)

        print(f"[OK] 청크 데이터 저장: {output_path}")
        return output_path

    def get_statistics(self) -> Dict:
        """청킹 통계"""
        if not self.chunks:
            return {}

        token_counts = [self.count_tokens(chunk['text']) for chunk in self.chunks]
        compliance_chunks = sum(1 for chunk in self.chunks
                              if chunk['metadata'].get('compliance_related', False))

        stats = {
            'total_chunks': len(self.chunks),
            'avg_tokens': sum(token_counts) / len(token_counts),
            'min_tokens': min(token_counts),
            'max_tokens': max(token_counts),
            'in_target_range': sum(1 for tc in token_counts if 250 <= tc <= 350),
            'compliance_related': compliance_chunks,
            'chunk_types': {}
        }

        # 청크 타입별 통계
        for chunk in self.chunks:
            chunk_type = chunk['metadata'].get('chunk_type', 'unknown')
            stats['chunk_types'][chunk_type] = stats['chunk_types'].get(chunk_type, 0) + 1

        return stats


def test_text_chunker():
    """텍스트 청킹 테스트"""
    print("="*60)
    print("텍스트 청킹 테스트")
    print("="*60)

    try:
        # 1. DOCX 로더로 문서 로드
        from docx_loader import DocxLoader

        doc_path = r"C:\kdy\Projects\Narutalk_V003\beta_v0031\database\raw_data\vector_db\좋은제약 내부 규정.docx"
        loader = DocxLoader(doc_path)

        print("\n1. 문서 로드...")
        loader.load_document()
        loader.extract_paragraphs()
        loader.extract_tables()
        structured_content = loader.get_structured_content()

        # 2. 청킹 수행
        print("\n2. 텍스트 청킹...")
        chunker = TextChunker()
        chunks = chunker.process_document(structured_content)
        print(f"   생성된 청크: {len(chunks)}개")

        # 3. 샘플 청크 출력
        print("\n3. 샘플 청크:")
        for chunk in chunks[:3]:
            metadata = chunk.get('metadata', {})
            print(f"\n   청크 ID: {metadata.get('chunk_id')}")
            print(f"   부: {metadata.get('part')}")
            print(f"   조항: {', '.join(metadata.get('article_nums', []))}")
            print(f"   토픽: {', '.join(metadata.get('topics', []))}")
            print(f"   준법관련: {metadata.get('compliance_related')}")
            print(f"   중요도: {metadata.get('importance_score')}")
            print(f"   텍스트: {chunk['text'][:100]}...")
            print(f"   토큰 수: {chunker.count_tokens(chunk['text'])}")

        # 4. 통계 출력
        print("\n4. 청킹 통계:")
        stats = chunker.get_statistics()
        print(f"   총 청크 수: {stats['total_chunks']}")
        print(f"   평균 토큰 수: {stats['avg_tokens']:.1f}")
        print(f"   최소/최대 토큰: {stats['min_tokens']}/{stats['max_tokens']}")
        print(f"   목표 범위(250-350) 내: {stats['in_target_range']}개 ({stats['in_target_range']/stats['total_chunks']*100:.1f}%)")
        print(f"   준법 관련 청크: {stats['compliance_related']}개")

        print("\n   청크 타입별:")
        for chunk_type, count in stats['chunk_types'].items():
            print(f"     - {chunk_type}: {count}개")

        # 5. 저장
        print("\n5. 청크 데이터 저장...")
        chunker.save_chunks('chunked_regulations.json')

        print("\n[OK] 텍스트 청킹 테스트 완료!")
        return chunker

    except Exception as e:
        print(f"\n[ERROR] 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    test_text_chunker()