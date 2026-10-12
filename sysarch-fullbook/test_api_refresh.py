import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler,HTTPServer
from unittest.mock import patch
from langflow_api import LangflowAPI

class RefreshTests(unittest.TestCase):
    def test_expired_session_is_refreshed_and_request_retried_once(self):
        counts={'protected':0,'login':0}
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):
                pass
            def do_GET(self):
                if self.path=='/auto_login':
                    counts['login']+=1
                    body={'access_token':'fresh-test-token'}
                else:
                    counts['protected']+=1
                    if self.headers.get('Authorization')!='Bearer fresh-test-token':
                        self.send_response(401);self.end_headers();self.wfile.write(b'expired');return
                    body={'ok':True}
                self.send_response(200);self.end_headers();self.wfile.write(json.dumps(body).encode())
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            api=LangflowAPI.__new__(LangflowAPI);api.token='expired-test-token'
            with patch('langflow_api.BASE',f'http://127.0.0.1:{server.server_port}'):
                try:
                    result=api.call('/protected')
                except RuntimeError:
                    result=None
                self.assertEqual(result,{'ok':True})
                self.assertEqual(counts,{'protected':2,'login':1})
        finally:
            server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()
