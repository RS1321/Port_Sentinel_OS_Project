import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch
import port_sentinel_agent as agent
import port_sentinel_tools as tools


def plan(action='inspect',port=8080,protocol='tcp',force=False):
    return dict(action=action,port=port,protocol=protocol,force=force)


class IntentTests(unittest.TestCase):
    def test_inspect(self):
        self.assertEqual(agent.validate_plan('What owns port 8080?',plan()),plan())
    def test_requested_stop(self):
        self.assertEqual(agent.validate_plan('What process is hogging port 8080? Stop it.',plan('stop'))['action'],'stop')
    def test_read_only_cannot_stop(self):
        with self.assertRaises(PermissionError): agent.validate_plan('What owns port 8080?',plan('stop'))
    def test_negative_and_conditional(self):
        for prompt in ['Do not stop port 8080','Never kill port 8080',"Don\u2019t kill port 8080",'If port 8080 is busy stop it','Explain how to stop port 8080']:
            with self.subTest(prompt=prompt),self.assertRaises(PermissionError): agent.validate_plan(prompt,plan('stop'))
    def test_wrong_port(self):
        with self.assertRaises(ValueError): agent.validate_plan('Stop port 8081',plan('stop'))
    def test_multiport(self):
        with self.assertRaises(ValueError): agent.validate_plan('Stop ports 8080 and 8081',plan('stop'))
    def test_invalid_types(self):
        for p in [plan(port=True),plan(port='8080'),plan(port=0),plan(force='false')]:
            with self.subTest(p=p),self.assertRaises(ValueError): agent.validate_plan('port 8080',p)
    def test_force_not_inferred(self):
        with self.assertRaises(PermissionError): agent.validate_plan('Stop port 8080',plan('stop',force=True))
    def test_force_explicit(self):
        self.assertTrue(agent.validate_plan('Force kill port 8080',plan('stop',force=True))['force'])
    def test_protocol_mismatch(self):
        with self.assertRaises(ValueError): agent.validate_plan('What owns UDP port 8080',plan())
    def test_unrequested_udp(self):
        with self.assertRaises(ValueError): agent.validate_plan('Stop port 8080',plan('stop',protocol='udp'))
    def test_both_stop_refused(self):
        with self.assertRaises(PermissionError): agent.validate_plan('Stop both protocols on port 8080',plan('stop',protocol='all'))
    def test_list(self):
        self.assertEqual(agent.validate_plan('List listening ports',plan('list',0,'all'))['action'],'list')
    def test_extra_fields(self):
        with self.assertRaises(ValueError): agent.validate_plan('port 8080',{**plan(),'command':'rm'})
    @patch.object(agent,'kill_process')
    @patch.object(agent,'find_port_process',return_value={'processes':[],'sockets':[]})
    def test_unknown_owner_never_signalled(self,find,kill):
        self.assertFalse(agent.execute_plan('Stop port 8080',plan('stop'))['success'])
        kill.assert_not_called()
    @patch.object(agent,'kill_process')
    @patch.object(agent,'find_port_process',return_value={'processes':[{'pid':10},{'pid':11}],'sockets':[]})
    def test_multiple_owners_never_signalled(self,find,kill):
        agent.execute_plan('Stop port 8080',plan('stop'))
        kill.assert_not_called()
    @patch.object(agent,'kill_process')
    @patch.object(agent,'find_port_process',return_value={'processes':[{'pid':10}],'sockets':[{'pids':[]}]})
    def test_hidden_owner_never_signalled(self,find,kill):
        agent.execute_plan('Stop port 8080',plan('stop'))
        kill.assert_not_called()


class SocketParsingTests(unittest.TestCase):
    def parse(self,text,proto):
        with patch.object(tools.subprocess,'run',return_value=subprocess.CompletedProcess([],0,text,'')):
            return tools._run_ss(proto)
    def test_tcp(self):
        row=self.parse('LISTEN 0 5 127.0.0.1:8080 0.0.0.0:* users:(("python3",pid=1234,fd=3))','tcp')[0]
        self.assertEqual((row['port'],row['pids'],row['protocol']),(8080,[1234],'tcp'))
    def test_combined_netid(self):
        rows=self.parse('tcp LISTEN 0 5 [::]:8080 [::]:* users:(("python3",pid=1234,fd=3))\nudp UNCONN 0 0 127.0.0.1:5353 0.0.0.0:* users:(("dns",pid=5678,fd=4))','all')
        self.assertEqual([(r['port'],r['protocol'],r['pids']) for r in rows],[(8080,'tcp',[1234]),(5353,'udp',[5678])])
    def test_malformed(self):
        self.assertEqual(self.parse('broken\nLISTEN 0 5 invalid *:*','tcp'),[])
    def test_hidden_pids(self):
        self.assertEqual(self.parse('LISTEN 0 5 127.0.0.1:8080 0.0.0.0:*','tcp')[0]['pids'],[])
    def test_ipv4_proc(self):
        self.assertEqual(tools._decode_address('0100007F:1F90','ipv4'),'127.0.0.1:8080')
    @unittest.skipUnless(sys.byteorder=='little','fixture is little endian')
    def test_ipv6_proc(self):
        self.assertEqual(tools._decode_address('00000000000000000000000001000000:1F90','ipv6'),'[::1]:8080')
    def test_timeout(self):
        with patch.object(tools.subprocess,'run',side_effect=subprocess.TimeoutExpired('ss',5)):
            with self.assertRaises(RuntimeError): tools._run_ss('tcp')
    @patch.object(tools.sys,'platform','linux')
    @patch.object(tools,'_enrich',side_effect=lambda rows: rows)
    @patch.object(tools,'_read_proc_socket_inodes')
    @patch.object(tools,'_run_ss')
    def test_partial_owner_supplement(self,ss,proc,enrich):
        base=dict(protocol='tcp',family='ipv4',source='ss',process_names=[])
        ss.return_value=[dict(base,port=80,local_address='127.0.0.1:80',pids=[1]),dict(base,port=8080,local_address='127.0.0.1:8080',pids=[])]
        proc.return_value=[dict(base,port=8080,local_address='127.0.0.1:8080',pids=[123])]
        with patch.object(tools,'_process_name',return_value='demo'):
            self.assertEqual(tools.list_listening_ports('tcp')[1]['pids'],[123])


@unittest.skipUnless(sys.platform=='linux','requires Ubuntu /proc and compiled native library')
class LinuxIntegrationTests(unittest.TestCase):
    def test_tcp_discover_stop_and_release(self):
        root=Path(__file__).resolve().parents[1]
        # A child binds an ephemeral port and prints it, avoiding fixed-port collisions.
        code='import socket,time; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); print(s.getsockname()[1],flush=True); time.sleep(30)'
        child=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,text=True)
        try:
            port=int(child.stdout.readline())
            found=tools.find_port_process(port)
            self.assertIn(child.pid,[p['pid'] for p in found['processes']])
            result=tools.kill_process(child.pid,expected_start=tools.process_identity(child.pid),port=port)
            self.assertTrue(result['port_released'],result)
            child.wait(timeout=3)
        finally:
            if child.poll() is None: child.kill(); child.wait()
            child.stdout.close()
    def test_native_protected_pid(self):
        from native_bridge import library,checked
        with self.assertRaises(PermissionError): checked(library().ps_open_process(1))
    def test_udp_proc_fallback(self):
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
            server.bind(('127.0.0.1',0))
            with patch.object(tools,'_run_ss',side_effect=RuntimeError('disabled')):
                found=tools.find_port_process(server.getsockname()[1],'udp')
            self.assertIn(os.getpid(),[p['pid'] for p in found['processes']])
    def test_service_transport_without_model(self):
        import tempfile
        import threading
        import port_sentinel_service as service
        with tempfile.TemporaryDirectory() as directory:
            path=str(Path(directory)/'test.sock')
            with patch.object(service,'run_agent',return_value='test response'):
                with service.socketserver.UnixStreamServer(path,service.Handler) as server:
                    thread=threading.Thread(target=server.handle_request)
                    thread.start()
                    self.assertEqual(agent.request_service('What owns port 8080?',path),'test response')
                    thread.join(timeout=5)
                    self.assertFalse(thread.is_alive())


if __name__=='__main__': unittest.main()
