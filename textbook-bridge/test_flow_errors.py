import io,unittest
from urllib.error import HTTPError
from flow_errors import failure_message
class FlowErrorTests(unittest.TestCase):
 def test_service_error_exposes_category_not_raw_body(self):
  e=HTTPError('http://localhost',500,'error',{},io.BytesIO(b'{"error":"Incomplete exam envelope","secret":"private"}'))
  result=failure_message(e);self.assertIn('格式',result);self.assertNotIn('private',result)
 def test_citation_and_timeout_are_distinct(self):
  self.assertIn('引用',failure_message(ValueError('Unknown answer citation')))
  self.assertIn('超时',failure_message(TimeoutError()))
