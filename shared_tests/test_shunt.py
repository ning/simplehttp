import logging
import sys
import os
import unittest
import subprocess
import signal
import time
import simplejson as json
import urllib
import tornado.httpclient

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
   format='%(asctime)s %(process)d %(filename)s %(lineno)d %(levelname)s #| %(message)s',
   datefmt='%H:%M:%S')

def http_fetch_json(endpoint, params=None, status_code=200, status_txt="OK", body=None):
    body = http_fetch(endpoint, params, 200, body)
    data = json.loads(body)
    assert data['status_code'] == status_code
    assert data['status_txt'] == status_txt
    return data['data']

def http_fetch(endpoint, params=None, response_code=200, body=None):
    http_client = tornado.httpclient.HTTPClient()
    url = 'http://127.0.0.1:8080' + endpoint
    if params:
        url += '?' + urllib.urlencode(params, doseq=1)
    method = "POST" if body else "GET"
    try:
        res = http_client.fetch(url, method=method, body=body)
    except tornado.httpclient.HTTPError, e:
        logging.info(e)
        res = e.response
    assert res.code == response_code
    return res.body


def valgrind_cmd(cmd, *options):
    assert isinstance(options, (list, tuple))
    assert cmd.startswith("/"), "valgrind_cmd must take a fully qualified executible path not %s" % cmd
    test_output_dir = os.path.join(os.path.dirname(cmd), "test_output")
    return [
        'valgrind',
        '-v',
        '--tool=memcheck',
        '--trace-children=yes',
        # '--demangle=yes',
        '--log-file=%s/vg.out' % test_output_dir,
        '--leak-check=full',
        '--show-reachable=yes',
        '--run-libc-freeres=yes',
        '%s' % cmd,
    ] + list(options)


def check_valgrind_output(filename):
    assert os.path.exists(filename)
    time.sleep(.15)
    vg_output = open(filename, 'r').readlines()
    logging.info('checking valgrind output %d lines' % len(vg_output))
    
    # strip the process prefix '==pid=='
    prefix_len = vg_output[0].find(' ')
    vg_output = [line[prefix_len+1:] for line in vg_output]
    
    error_summary = [line.strip() for line in vg_output if line.startswith("ERROR SUMMARY:")]
    assert error_summary, "vg.out not finished"
    assert error_summary[0].startswith("ERROR SUMMARY: 0 errors")
    
    lost = [line.strip() for line in vg_output if line.strip().startswith("definitely lost:")]
    assert lost
    assert lost[0] == "definitely lost: 0 bytes in 0 blocks"
    
    lost = [line.strip() for line in vg_output if line.strip().startswith("possibly lost:")]
    assert lost
    assert lost[0] == "possibly lost: 0 bytes in 0 blocks"


class SubprocessTest(unittest.TestCase):
    process_options = []
    binary_name = ""
    working_dir = None
    def setUp(self):
        """setup method that starts up mongod instances using `self.mongo_options`"""
        self.temp_dirs = []
        self.processes = []
        assert self.binary_name, "you must override self.binary_name"
        assert self.working_dir, "set workign dir to os.path.dirname(__file__)"
        
        exe = os.path.join(self.working_dir, self.binary_name)
        if os.path.exists(exe):
            logging.info('removing old %s' % exe)
            os.unlink(exe)
        
        logging.info('running make')
        pipe = subprocess.Popen(['make'])
        pipe.wait()
        
        assert os.path.exists(exe), "compile failed"
        
        test_output_dir = os.path.join(self.working_dir, "test_output")
        if os.path.exists(test_output_dir):
            logging.info('removing %s' % test_output_dir)
            pipe = subprocess.Popen(['rm', '-rf', test_output_dir])
            pipe.wait()
        
        if not os.path.exists(test_output_dir):
            os.makedirs(test_output_dir)
        
        for options in self.process_options:
            
            logging.info(' '.join(options))
            # self.stdout = open(test_output_dir + '/test.out', 'w')
            # self.stderr = open(test_output_dir + '/test.err', 'w')
            pipe = subprocess.Popen(options)#, stdout=self.stdout, stderr=self.stderr)
            self.processes.append(pipe)
            logging.debug('started process %s' % pipe.pid)
        
        self.wait_for('http://127.0.0.1:8080/', max_time=5)
    
    def wait_for(self, url, max_time):
        # check up to 15 times till the endpoint specified is available waiting max_time
        step = max_time / float(15)
        http = tornado.httpclient.HTTPClient()
        for x in range(15):
            try:
                logging.info('try number %d for %s' % (x, url))
                http.fetch(url, connect_timeout=.5, request_timeout=.5)
                return
            except:
                pass
            time.sleep(step)
    
    def graceful_shutdown(self):
        try:
            http_fetch('/exit', dict())
        except:
            # we never get a reply if this works correctly
            time.sleep(1)
    
    def tearDown(self):
        """teardown method that cleans up child mongod instances, and removes their temporary data files"""
        logging.debug('teardown')
        try:
            self.graceful_shutdown()
        except:
            logging.exception('failed graceful shutdown')
        
        for process in self.processes:
            logging.info('%s' % process.poll())
            if process.poll() is None:
                logging.debug('killing process %s' % process.pid)
                os.kill(process.pid, signal.SIGKILL)
                process.wait()
        for dirname in self.temp_dirs:
            logging.debug('cleaning up %s' % dirname)
            pipe = subprocess.Popen(['rm', '-rf', dirname])
            pipe.wait()
        check_valgrind_output('test_output/vg.out')
