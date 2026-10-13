import asyncio,importlib.util,json,tempfile,unittest,threading,time
from pathlib import Path
module_path=Path(__file__).with_name('streaming.py')
spec=importlib.util.spec_from_file_location('streaming',module_path) if module_path.exists() else None
stream=importlib.util.module_from_spec(spec) if spec else None
if stream:spec.loader.exec_module(stream)

class StreamingTests(unittest.TestCase):
 def test_explicit_langflow_stream_false_is_enabled_on_a_copy(self):
  self.assertIsNotNone(stream);updates=[];original=None
  async def run():
   nonlocal original
   with tempfile.TemporaryDirectory() as root:
    box=stream.Mailbox('11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',root)
    class Model:
     streaming=False
     def model_copy(self,update):updates.append(update);copy=Model();copy.streaming=update['streaming'];return copy
     async def astream(self,messages):
      if not self.streaming:raise AssertionError('Langflow handle remains non-streaming')
      yield type('Chunk',(),{'content':'<final_answer>正文</final_answer>'})()
    original=Model()
    try:await stream.consume_model(original,[],box,'qa')
    finally:box.cleanup()
  asyncio.run(run());self.assertEqual(updates,[{'streaming':True}]);self.assertFalse(original.streaming)
 def test_minimax_stream_separates_reasoning_without_disabling_it(self):
  self.assertIsNotNone(stream);seen=[]
  async def run():
   with tempfile.TemporaryDirectory() as root:
    box=stream.Mailbox('11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',root)
    class Model:
     model_name='MiniMax-M3'
     async def astream(self,messages,**kwargs):seen.append(kwargs);yield type('Chunk',(),{'content':'<final_answer>正文</final_answer>'})()
    try:await stream.consume_model(Model(),[],box,'qa')
    finally:box.cleanup()
  asyncio.run(run());self.assertEqual(seen,[{'extra_body':{'reasoning_split':True}}])
 def test_monitor_shutdown_never_blocks_final_delivery_on_cloud(self):
  self.assertIsNotNone(stream);started=threading.Event();release=threading.Event();calls=[]
  def cloud(body):calls.append(body['action']);started.set();release.wait(.3);return {}
  with tempfile.TemporaryDirectory() as root:
   monitor=stream.StreamMonitor({'id':'11111111-1111-4111-8111-111111111111','lease':'22222222-2222-4222-8222-222222222222'},cloud)
   monitor.start();self.assertTrue(started.wait(1));before=time.monotonic()
   try:monitor.close();self.assertLess(time.monotonic()-before,.1);self.assertEqual(calls,['control'])
   finally:release.set();monitor.thread.join(1);monitor.box.cleanup()
 def test_split_tags_hide_think_and_structured_fields(self):
  self.assertIsNotNone(stream,'Missing streaming module')
  raw='<think>private</think><final_answer>正文[片段1]</final_answer><used_figures>[]</used_figures><practice>secret</practice>'
  for i in range(len(raw)+1):
   value=stream.visible_answer(raw[:i],'qa')
   self.assertNotIn('private',value);self.assertNotIn('secret',value);self.assertNotIn('<',value)
  self.assertEqual(stream.visible_answer(raw,'qa'),'正文[片段1]')
  self.assertEqual(stream.visible_answer('<think><final_answer>private','qa'),'')
 def test_mixed_and_general_have_source_disclaimers(self):
  self.assertIsNotNone(stream)
  self.assertIn('AI 知识补充',stream.visible_answer('<final_answer>通用解释','qa_fallback'))
  value=stream.visible_answer('<final_answer>教材解释</final_answer><used_figures>[]</used_figures><ai_supplement>补充','qa_mixed')
  self.assertIn('教材依据',value);self.assertIn('非教材原文',value);self.assertIn('补充',value)
 def test_mailbox_sequence_reset_cancel_and_cleanup(self):
  self.assertIsNotNone(stream)
  with tempfile.TemporaryDirectory() as root:
   box=stream.Mailbox('11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',root)
   box.publish('first');box.publish('');self.assertEqual(box.read()['seq'],2);box.cancel();self.assertTrue(box.cancelled());box.cleanup();self.assertFalse(box.directory.exists())
  with self.assertRaises(ValueError):stream.Mailbox('../escape','invalid')
 def test_waiting_model_stream_is_cancelled(self):
  self.assertIsNotNone(stream)
  async def run():
   with tempfile.TemporaryDirectory() as root:
    box=stream.Mailbox('11111111-1111-4111-8111-111111111111','22222222-2222-4222-8222-222222222222',root)
    class Model:
     async def astream(self,messages):
      yield type('Chunk',(),{'content':'<final_answer>开始'})()
      await asyncio.sleep(10)
    async def stop():await asyncio.sleep(.1);box.cancel()
    stopper=asyncio.create_task(stop())
    try:
     with self.assertRaises(stream.GenerationStopped):await asyncio.wait_for(stream.consume_model(Model(),[],box,'qa'),2)
     self.assertEqual(box.read()['text'],'开始')
    finally:await stopper;box.cleanup()
  asyncio.run(run())

if __name__=='__main__':unittest.main()
