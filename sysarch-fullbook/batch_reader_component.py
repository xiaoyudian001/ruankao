import json
from pathlib import Path
from lfx.custom import Component
from lfx.io import StrInput, Output
from lfx.schema.dataframe import DataFrame

class FullBookBatchReader(Component):
    display_name='读取已解析教材分片'
    description='读取本机缓存的教材分片及原PDF页码，供批量入库。'
    name='FullBookBatchReader'
    icon='FileText'
    inputs=[StrInput(name='batch_file',display_name='分片JSON路径',required=True)]
    outputs=[Output(name='rows',display_name='带来源的文本块',method='load_rows')]

    def load_rows(self)->DataFrame:
        root=Path(r'F:\daily\output\sysarch-fullbook-v2').resolve()
        path=Path(self.batch_file).resolve()
        if not path.is_relative_to(root) or path.suffix!='.json':
            raise ValueError('分片文件必须位于教材全书缓存目录内。')
        rows=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(rows,list) or not rows:
            raise ValueError('没有可入库的文本块。')
        for row in rows:
            if not row.get('text','').strip() or not row.get('chunk_id'):
                raise ValueError('文本或稳定分片标识缺失。')
            if int(row['pdf_page_start'])<1 or int(row['pdf_page_end'])<int(row['pdf_page_start']):
                raise ValueError('原PDF页码无效。')
        self.status=f'加载{len(rows)}个带页码的文本块'
        return DataFrame(rows)
