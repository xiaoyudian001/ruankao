"""Print final answers and bounded evidence for manual review, without raw thinking."""
import argparse
import json
from pathlib import Path
from answer_cleanup import clean_answer

ROOT = Path(r'F:\daily\output\sysarch-rag-evaluation')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run')
    parser.add_argument('--questions', required=True)
    parser.add_argument('--evidence', type=int, default=0)
    args = parser.parse_args()
    tests = {q['id']: q for q in json.loads((ROOT/'dataset.json').read_text(encoding='utf-8'))['tests']}
    for qid in args.questions.split(','):
        q = json.loads((ROOT/args.run/(qid+'.json')).read_text(encoding='utf-8'))
        print(json.dumps({'id': qid, 'question': q['question'], 'points': tests[qid]['required_points'],
                          'plan': q['query_plan'], 'answer': clean_answer(q['answer']),
                          'chunks': [{k: c.get(k) for k in ('chunk_id', 'chapter', 'book_pages', 'pdf_pages')} |
                                     ({'content': c['content'][:args.evidence]} if args.evidence else {})
                                     for c in q['retrieved_chunks']]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
