import unittest
from screenshots import parse_recognition,recognition_wire,validate_question_images
class ScreenshotTests(unittest.TestCase):
 def test_transcription_contract(self):
  self.assertEqual(parse_recognition('<recognized_question>哪项正确？\nA.甲\nB.乙</recognized_question><recognition_notes>核对B</recognition_notes>')['notes'],'核对B')
  for raw in ['答案A','<recognized_question></recognized_question><recognition_notes></recognition_notes>']:
   with self.assertRaises(ValueError):parse_recognition(raw)
 def test_question_images_not_textbook_sources(self):
  import base64,struct
  raw=b'\x89PNG\r\n\x1a\n'+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',600,800)+b'\x00'*16
  images=[{'dataUrl':'data:image/png;base64,'+base64.b64encode(raw).decode(),'width':600,'height':800}]
  wire=recognition_wire(images);self.assertEqual(wire['taskType'],'recognize');self.assertEqual(wire['references'],[])
  self.assertEqual(validate_question_images(images),images)
  with self.assertRaises(ValueError):validate_question_images(images*3)
  with self.assertRaises(ValueError):validate_question_images([{'dataUrl':'https://bad/image','width':600,'height':800}])
if __name__=='__main__':unittest.main()
