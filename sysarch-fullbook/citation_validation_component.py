"""Self-contained Langflow final cleaner, preserving each flow's legacy cleanup."""
from pathlib import Path

HERE = Path(__file__).parent
PURE = '\n\n'.join((HERE / name).read_text(encoding='utf-8') for name in
                     ['citation_format.py', 'answer_cleanup.py', 'answer_citations.py', 'source_references.py'])
PURE = PURE.replace('from citation_format import source_hint\n', '')


def cleaner_code(legacy_code):
    cleanup = 'clean_answer' if 'def clean_answer(' in legacy_code else 'strip_think'
    return PURE + '''

from lfx.custom.custom_component.component import Component
from lfx.io import MessageInput, HandleInput, Output
from lfx.schema.message import Message
from lfx.schema.data import Data
from lfx.schema.dataframe import DataFrame


class FinalAnswerCleaner(Component):
    display_name = '最终答案清理与引用校验'
    description = '隐藏think；依据同次检索元数据填写完整出处。仅校验引用来源格式，不判定结论正确性。'
    icon = 'Filter'
    name = 'FinalAnswerCleaner'
    inputs = [
        MessageInput(name='input_message', display_name='模型回答', required=True),
        HandleInput(name='reference_data', display_name='本次检索片段',
                    input_types=['DataFrame','Table','Data','JSON'], required=True),
    ]
    outputs = [Output(name='cleaned_message', display_name='最终答案', method='clean_message')]

    def _rows(self):
        value = self.reference_data
        if isinstance(value, DataFrame):
            return [r.to_dict() for _, r in value.iterrows()]
        if isinstance(value, Data):
            return [value.data]
        if isinstance(value, list) and all(isinstance(r, Data) for r in value):
            return [r.data for r in value]
        if isinstance(value, dict) and 'data' in value:
            if 'columns' in value:
                return [r.to_dict() for _, r in DataFrame.from_dict(value).iterrows()]
            return [Data(**value).data]
        raise ValueError('引用校验需要与Parser相同顺序的本次检索表。')

    def clean_message(self) -> Message:
        text = CLEANUP(self.input_message.get_text())
        rows = self._rows()
        result = normalize_citations(text, rows)
        self.status = {k:v for k,v in result.items() if k != 'text'}
        return Message(text=result['text'], session_metadata={'textbook_refs': source_references(rows)})
'''.replace('CLEANUP(', cleanup + '(')
