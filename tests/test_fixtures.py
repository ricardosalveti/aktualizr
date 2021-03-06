import subprocess
import logging
import json
import tempfile
import threading
import os

from os import devnull
from os import path
from uuid import uuid4
from os import urandom
from functools import wraps
from http.server import SimpleHTTPRequestHandler, HTTPServer

from fake_http_server.fake_test_server import FakeTestServerBackground


logger = logging.getLogger(__name__)


class Aktualizr:

    def __init__(self, aktualizr_primary_exe, aktualizr_info_exe, id,
                 uptane_server, ca, pkey, cert, wait_port=9040, wait_timeout=60, secondary=None, output_logs=True,
                 run_mode='once', director=None, image_repo=None, **kwargs):
        self.id = id

        self._aktualizr_primary_exe = aktualizr_primary_exe
        self._aktualizr_info_exe = aktualizr_info_exe
        self._storage_dir = tempfile.TemporaryDirectory()

        with open(path.join(self._storage_dir.name, 'secondary_config.json'), 'w+') as secondary_config_file:
            secondary_cfg = json.loads(Aktualizr.SECONDARY_CONFIG_TEMPLATE.format(port=wait_port, timeout=wait_timeout))
            json.dump(secondary_cfg, secondary_config_file)
            self._secondary_config_file = secondary_config_file.name

        with open(path.join(self._storage_dir.name, 'config.toml'), 'w+') as config_file:
            config_file.write(Aktualizr.CONFIG_TEMPLATE.format(server_url=uptane_server.base_url,
                                                               ca_path=ca, pkey_path=pkey, cert_path=cert,
                                                               serial=id[1], hw_ID=id[0],
                                                               storage_dir=self._storage_dir,
                                                               db_path=path.join(self._storage_dir.name, 'sql.db'),
                                                               secondary_cfg_file=self._secondary_config_file,
                                                               director=director.base_url if director else '',
                                                               image_repo=image_repo.base_url if image_repo else ''))
            self._config_file = config_file.name

        self.add_secondary(secondary) if secondary else None
        self._output_logs = output_logs
        self._run_mode = run_mode

    CONFIG_TEMPLATE = '''
    [tls]     
    server = "{server_url}"

    [import]
    tls_cacert_path = "{ca_path}"
    tls_pkey_path = "{pkey_path}"
    tls_clientcert_path = "{cert_path}"

    [provision]
    primary_ecu_serial = "{serial}"
    primary_ecu_hardware_id = "{hw_ID}"

    [storage]
    path = "{storage_dir}"
    type = "sqlite"
    sqldb_path = "{db_path}"

    [pacman]
    type = "fake"

    [uptane]
    polling_sec = 0
    secondary_config_file = "{secondary_cfg_file}"
    director_server = "{director}"
    repo_server = "{image_repo}"

    [logger]
    loglevel = 1

    '''

    SECONDARY_CONFIG_TEMPLATE = '''
    {{
      "IP": {{
        "secondaries_wait_port": {port},
        "secondaries_wait_timeout": {timeout},
        "secondaries": []
      }}
    }}
    '''

    def add_secondary(self, secondary):
        with open(self._secondary_config_file, "r+") as config_file:
            sec_cfg = json.load(config_file)
            sec_cfg["IP"]["secondaries"].append({"addr": "127.0.0.1:{}".format(secondary.port)})
            config_file.seek(0)
            json.dump(sec_cfg, config_file)

    def update_wait_timeout(self, timeout):
        with open(self._secondary_config_file, "r+") as config_file:
            sec_cfg = json.load(config_file)
            sec_cfg["IP"]["secondaries_wait_timeout"] = timeout
            config_file.seek(0)
            json.dump(sec_cfg, config_file)

    def run(self, run_mode):
        subprocess.run([self._aktualizr_primary_exe, '-c', self._config_file, '--run-mode', run_mode], check=True)

    def get_info(self):

        info_exe_res = None
        for ii in range(0, 3):
            info_exe_res = subprocess.run([self._aktualizr_info_exe, '-c', self._config_file],
                                          timeout=60, stdout=subprocess.PIPE)
            if info_exe_res.returncode == 0:
                break

        if info_exe_res and info_exe_res.returncode == 0:
            return str(info_exe_res.stdout)
        else:
            return None

    # ugly stuff that could be removed if Aktualizr had exposed API to check status
    # or aktializr-info had output status/info in a structured way (e.g. json)
    def is_ecu_registered(self, ecu_id):
        device_status = self.get_info()
        if not ((device_status.find(ecu_id[0]) != -1) and (device_status.find(ecu_id[1]) != -1)):
            return False
        not_registered_field = "Removed or not registered ecus:"
        not_reg_start = device_status.find(not_registered_field)
        return not_reg_start == -1 or (device_status.find(ecu_id[1], not_reg_start) == -1)

    def get_current_image_info(self, ecu_id):
        if self.id == ecu_id:
            return self.get_current_primary_image_info()
        else:
            return self._get_current_image_info(ecu_id)

    # applicable only to secondary ECUs due to inconsistency in presenting information
    # about primary and secondary ECUs
    # ugly stuff that could be removed if Aktualizr had exposed API to check status
    # or aktializr-info had output status/info in a structured way (e.g. json)
    def _get_current_image_info(self, ecu_id):
        secondary_image_hash_field = 'installed image hash: '
        secondary_image_filename_field = 'installed image filename: '
        aktualizr_status = self.get_info()
        ecu_serial = ecu_id[1]
        ecu_info_position = aktualizr_status.find(ecu_serial)
        if ecu_info_position == -1:
            return None

        start = aktualizr_status.find(secondary_image_hash_field, ecu_info_position)
        end = aktualizr_status.find('\\n', start)
        hash_val = aktualizr_status[start + len(secondary_image_hash_field):end]

        # start = aktualizr_status.find(secondary_image_filename_field, ecu_info_position)
        # end = aktualizr_status.find('\\n', start)
        # filename_val = aktualizr_status[start + len(secondary_image_filename_field):end]

        return hash_val

    # ugly stuff that could be removed if Aktualizr had exposed API to check status
    # or aktializr-info had output status/info in a structured way (e.g. json)
    def get_current_primary_image_info(self):
        primary_hash_field = 'Current primary ecu running version: '
        aktualizr_status = self.get_info()
        start = aktualizr_status.find(primary_hash_field)
        end = aktualizr_status.find('\\n', start)
        return aktualizr_status[start + len(primary_hash_field):end]

    def __enter__(self):
        self._process = subprocess.Popen([self._aktualizr_primary_exe, '-c', self._config_file, '--run-mode', self._run_mode],
                                         stdout=None if self._output_logs else open(devnull, 'w'), close_fds=True)
        logger.debug("Aktualizr has been started")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._process.terminate()
        self._process.wait(timeout=60)
        logger.debug("Aktualizr has been stopped")

    def wait_for_completion(self, timeout=60):
        self._process.wait(timeout)


class KeyStore:
    base_dir = "./"

    @staticmethod
    def ca():
        return path.join(KeyStore.base_dir, 'tests/test_data/prov_selfupdate/ca.pem')

    @staticmethod
    def pkey():
        return path.join(KeyStore.base_dir, 'tests/test_data/prov_selfupdate/pkey.pem')

    @staticmethod
    def cert():
        return path.join(KeyStore.base_dir, 'tests/test_data/prov_selfupdate/client.pem')


class IPSecondary:

    def __init__(self, aktualizr_secondary_exe, id, port=9050, primary_port=9040):
        self.id = id
        self.port = port

        self._aktualizr_secondary_exe = aktualizr_secondary_exe
        self._storage_dir = tempfile.TemporaryDirectory()

        with open(path.join(self._storage_dir.name, 'config.toml'), 'w+') as config_file:
            config_file.write(IPSecondary.CONFIG_TEMPLATE.format(serial=id[1], hw_ID=id[0],
                                                                 port=port, primary_port=primary_port,
                                                                 storage_dir=self._storage_dir,
                                                                 db_path=path.join(self._storage_dir.name, 'db.sql')))
            self._config_file = config_file.name

    CONFIG_TEMPLATE = '''
    [uptane]
    ecu_serial = "{serial}"
    ecu_hardware_id = "{hw_ID}"

    [network]
    port = {port}
    primary_ip = "127.0.0.1"
    primary_port = {primary_port}

    [storage]
    type = "sqlite"
    path = "{storage_dir}"
    sqldb_path = "{db_path}"


    [pacman]
    type = "fake"
    '''

    def is_running(self):
        return True if self._process.poll() is None else False

    def __enter__(self):
        self._process = subprocess.Popen([self._aktualizr_secondary_exe, '-c', self._config_file],
                                         stdout=open(devnull, 'w'), close_fds=True)
        logger.debug("IP Secondary {} has been started: {}".format(self.id, self.port))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._process.terminate()
        self._process.wait(timeout=60)
        logger.debug("IP Secondary {} has been stopped".format(self.id))


class UptaneRepo(HTTPServer):
    def __init__(self, doc_root, ifc, port, client_handler_map={}):
        super(UptaneRepo, self).__init__(server_address=(ifc, port), RequestHandlerClass=self.Handler)

        self.base_url = 'http://{}:{}'.format(ifc, port)
        self.doc_root = doc_root
        self._server_thread = None

        self.Handler.do_POST = \
            lambda request: (self.Handler.handler_map.get('POST', {})).get(request.path,
                                                                           self.Handler.default_handler)(request)

        self.Handler.do_PUT = \
            lambda request: (self.Handler.handler_map.get('PUT', {})).get(request.path,
                                                                          self.Handler.default_handler)(request)

        self.Handler.do_GET = \
            lambda request: (self.Handler.handler_map.get('GET', {})).get(request.path,
                                                                          self.Handler.default_get)(request)

        for method, method_handlers in client_handler_map.items():
            for url, handler in method_handlers.items():
                if self.Handler.handler_map.get(method, None) is None:
                    self.Handler.handler_map[method] = {}
                self.Handler.handler_map[method][url] = handler

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, request, client_address, server):
            self.doc_root = server.doc_root
            self.disable_nagle_algorithm = True
            super(UptaneRepo.Handler, self).__init__(request, client_address, server)

        def default_handler(self):
            self.send_response(200)
            self.end_headers()

        def default_get(self):
            self.send_response(200)
            self.end_headers()
            with open(self.file_path, 'rb') as source:
                self.copyfile(source, self.wfile)

        handler_map = {}

        @property
        def file_path(self):
            return os.path.join(self.doc_root, self.path[1:])

    def start(self):
        self._server_thread = threading.Thread(target=self.serve_forever)
        self._server_thread.start()
        return self

    def stop(self):
        self.shutdown()
        self.server_close()
        if self._server_thread:
            self._server_thread.join(timeout=60)
            self._server_thread = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()


class DirectorRepo(UptaneRepo):
    """
    This server
     - serves signed metadata about images
     - receives device manifest which includes installation report if any installation has happened
    """

    director_subdir = "repo/director"

    def __init__(self, uptane_repo_root, ifc, port, client_handler_map={}):
        super(DirectorRepo, self).__init__(os.path.join(uptane_repo_root, self.director_subdir), ifc=ifc, port=port,
                                           client_handler_map=client_handler_map)

        self._install_event = threading.Event()
        self._install_event.clear()
        self._last_install_res = False
        self._last_install_res_lock = threading.RLock()

    class Handler(UptaneRepo.Handler):
        def handle_manifest(self):
            self.send_response(200)
            self.end_headers()
            json_data = None
            try:
                data_size = int(self.headers['Content-Length'])
                data_string = self.rfile.read(data_size)
                json_data = json.loads(data_string)
            except Exception as exc:
                logger.error(exc)

            if json_data:
                install_report = json_data['signed'].get('installation_report', "")
                if install_report:
                    self.server.set_install_event(install_report['report']['result']['success'])

        handler_map = {'PUT': {'/manifest': handle_manifest}}

    def set_install_event(self, result):
        with self._last_install_res_lock:
            self._last_install_res = result
        self._install_event.set()

    def wait_for_install(self, timeout=120):
        self._install_event.wait(timeout=timeout)

    def is_install_successful(self):
        with self._last_install_res_lock:
            return self._last_install_res


class ImageRepo(UptaneRepo):
    """
    This server serves signed metadata about images
    as well as images by default (it's possible to serve images from another server by using the 'custom URI' feature)
    """

    image_subdir = "repo/repo"

    def __init__(self, uptane_repo_root, ifc, port, client_handler_map={}):
        super(ImageRepo, self).__init__(os.path.join(uptane_repo_root, self.image_subdir), ifc=ifc, port=port,
                                        client_handler_map=client_handler_map)


class CustomRepo(UptaneRepo):
    """
    This server serves images
    """
    image_subdir = "repo/repo"

    def __init__(self, root, ifc, port, client_handler_map={}):
        super(CustomRepo, self).__init__(os.path.join(root, self.image_subdir),
                                         ifc=ifc, port=port, client_handler_map=client_handler_map)


class DownloadInterruptionHandler:
    def __init__(self, number_of_failures=1, bytes_to_send_before_interruption=10, url=''):
        self._bytes_to_send_before_interruption = bytes_to_send_before_interruption
        self._number_of_failures = number_of_failures
        self._failure_counter = 0
        self._url = url

    def __call__(self, request_handler):
        if self._failure_counter < self._number_of_failures:
            request_handler.send_response(200)
            file_size = os.path.getsize(request_handler.file_path)
            request_handler.send_header('Content-Length', file_size)
            request_handler.end_headers()

            with open(request_handler.file_path, 'rb') as source:
                data = source.read(self._bytes_to_send_before_interruption)
                request_handler.wfile.write(data)

            self._failure_counter += 1
        else:
            request_handler.default_get()

    def map(self, url=''):
        return {'GET': {url if url else self._url: DownloadInterruptionHandler(self._number_of_failures,
                                                                               self._bytes_to_send_before_interruption)}}


class MalformedImageHandler:
    def __init__(self, number_of_failures=1, url=''):
        self._number_of_failures = number_of_failures
        self._failure_counter = 0
        self._url = url

    def __call__(self, request_handler):
        if self._failure_counter < self._number_of_failures:
            request_handler.send_response(200)
            request_handler.end_headers()
            request_handler.wfile.write(b'malformed image')

            self._failure_counter += 1
        else:
            request_handler.default_get()

    def map(self, url):
        return {'GET': {url if url else self._url: MalformedImageHandler(self._number_of_failures)}}


class SlowRetrievalHandler:
    def __init__(self, number_of_failures=1, url=''):
        self._number_of_failures = number_of_failures
        self._failure_counter = 0
        self._url = url

    def __call__(self, request_handler):
        if self._failure_counter < self._number_of_failures:
            request_handler.send_response(200)
            file_size = os.path.getsize(request_handler.file_path)
            request_handler.end_headers()

            with open(request_handler.file_path, 'rb') as source:
                while True:
                    data = source.read(1)
                    if not data:
                        break
                    request_handler.wfile.write(data)
                    request_handler.wfile.flush()
                    import time
                    time.sleep(100)

            self._failure_counter += 1
        else:
            request_handler.default_get()

    def map(self, url):
        return {'GET': {url if url else self._url: SlowRetrievalHandler(self._number_of_failures)}}


class RedirectHandler:
    def __init__(self, number_of_redirects=1, url=''):
        self._number_of_redirects = number_of_redirects
        self._redirect_counter = 0
        self._url = url

    def __call__(self, request_handler):
        if self._redirect_counter < self._number_of_redirects:
            request_handler.send_response(301)
            request_handler.send_header('Location', request_handler.server.base_url + request_handler.path)
            request_handler.end_headers()
            self._redirect_counter += 1
        else:
            request_handler.default_get()

    def map(self, url):
        return {'GET': {url if url else self._url: RedirectHandler(self._number_of_redirects)}}


class MalformedJsonHandler:
    def __init__(self, number_of_failures=1):
        self._number_of_failures = number_of_failures
        self._failure_counter = 0

    def __call__(self, request_handler):
        if self._failure_counter < self._number_of_failures:
            request_handler.send_response(200)
            request_handler.end_headers()
            request_handler.wfile.write(b'{"non-uptane-json": "some-value"}')

            self._failure_counter += 1
        else:
            request_handler.default_get()

    def map(self, url):
        return {'GET': {url: MalformedJsonHandler(self._number_of_failures)}}


class UptaneTestRepo:

    def __init__(self, repo_manager_exe, server_port=8080, director_port=8889, image_repo_port=8890,
                 custom_repo_port=8891):
        self.image_rel_dir = 'repo/repo'
        self.target_rel_dir = 'repo/repo/targets'

        self._repo_manager_exe = repo_manager_exe
        self._repo_root_dir = tempfile.TemporaryDirectory()

        self.server_port = server_port
        self.director_port = director_port
        self.image_repo_port = image_repo_port
        self.custom_repo_port = custom_repo_port

    def create_generic_server(self, **kwargs):
        return FakeTestServerBackground(meta_path=self.root_dir,
                                        target_path=self.target_dir,
                                        port=self.server_port, **kwargs)

    def create_director_repo(self, handler_map={}):
        return DirectorRepo(self.root_dir, 'localhost', self.director_port, client_handler_map=handler_map)

    def create_image_repo(self, handler_map={}):
        return ImageRepo(self.root_dir, 'localhost', self.image_repo_port, client_handler_map=handler_map)

    def create_custom_repo(self, handler_map={}):
        return CustomRepo(self.root_dir, 'localhost', self.custom_repo_port, client_handler_map=handler_map)

    @property
    def root_dir(self):
        return self._repo_root_dir.name

    @property
    def image_dir(self):
        return path.join(self.root_dir, self.image_rel_dir)

    @property
    def target_dir(self):
        return path.join(self.root_dir, self.target_rel_dir)

    @property
    def target_file(self):
        return path.join(self.image_dir, 'targets.json')

    def add_image(self, id, image_filename, target_name=None, image_size=1024, custom_url=''):

        targetname = target_name if target_name else image_filename

        with open(path.join(self.image_dir, image_filename), 'wb') as image_file:
            image_file.write(urandom(image_size))

        image_creation_cmdline = [self._repo_manager_exe, '--path', self.root_dir,
                                  '--command', 'image', '--filename', image_filename, '--targetname', targetname, '--hwid', id[0]]

        if custom_url:
            image_creation_cmdline.append('--url')
            image_creation_cmdline.append(custom_url)

        subprocess.run(image_creation_cmdline, cwd=self.image_dir, check=True)

        # update the director metadata
        subprocess.run([self._repo_manager_exe, '--path', self.root_dir,
                        '--command', 'addtarget', '--targetname', targetname,
                        '--hwid', id[0], '--serial', id[1]], check=True)

        # sign so the image becomes available for an update for a client/device
        subprocess.run([self._repo_manager_exe, '--path', self.root_dir, '--command', 'signtargets'], check=True)

        with open(self.target_file, "r") as target_file:
            targets = json.load(target_file)
            target_hash = targets["signed"]["targets"][targetname]["hashes"]["sha256"]

        return target_hash

    def __enter__(self):
        self._generate_repo()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._repo_root_dir.cleanup()

    def _generate_repo(self):
        subprocess.run([self._repo_manager_exe, '--path', self.root_dir, '--command', 'generate'], check=True)


def with_aktualizr(start=True, output_logs=False, id=('primary-hw-ID-001', str(uuid4())), wait_timeout=60,
                   aktualizr_primary_exe='src/aktualizr_primary/aktualizr',
                   aktualizr_info_exe='src/aktualizr_info/aktualizr-info',
                   run_mode='once'):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, **kwargs):
            aktualizr = Aktualizr(aktualizr_primary_exe=aktualizr_primary_exe,
                           aktualizr_info_exe=aktualizr_info_exe,
                           id=id, ca=KeyStore.ca(), pkey=KeyStore.pkey(), cert=KeyStore.cert(),
                                  wait_timeout=wait_timeout, output_logs=output_logs,
                           run_mode=run_mode, **kwargs)
            if start:
                with aktualizr:
                    result = test(*args, **kwargs, aktualizr=aktualizr)
            else:
                result = test(*args, **kwargs, aktualizr=aktualizr)
            return result
        return wrapper
    return decorator


# The following decorators can be eliminated if pytest framework (or similar) is used
# by using fixtures instead
def with_uptane_backend(start_generic_server=True, port=8080,
                        repo_manager_exe='src/uptane_generator/uptane-generator'):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, **kwargs):
            repo_manager_exe_abs_path = path.abspath(repo_manager_exe)
            with UptaneTestRepo(repo_manager_exe_abs_path, server_port=port) as repo:
                if start_generic_server:
                    with repo.create_generic_server() as uptane_server:
                        result = test(*args, **kwargs, uptane_repo=repo, uptane_server=uptane_server)
                else:
                    result = test(*args, **kwargs, uptane_repo=repo)
            return result
        return wrapper
    return decorator


def with_director(start=True, handlers=[]):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, uptane_repo, **kwargs):
            def func(handler_map={}):
                director = uptane_repo.create_director_repo(handler_map=handler_map)
                if start:
                    with director:
                        result = test(*args, **kwargs, uptane_repo=uptane_repo, director=director)
                else:
                    result = test(*args, **kwargs, uptane_repo=uptane_repo, director=director)
                return result

            if handlers and len(handlers) > 0:
                for handler in handlers:
                    result = func(handler.map(kwargs.get('test_path', '')))
                    if not result:
                        break
            else:
                result = func()
            return result
        return wrapper
    return decorator


def with_imagerepo(start=True, handlers=[]):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, uptane_repo, **kwargs):
            def func(handler_map={}):
                image_repo = uptane_repo.create_image_repo(handler_map=handler_map)
                if start:
                    with image_repo:
                        result = test(*args, **kwargs, uptane_repo=uptane_repo, image_repo=image_repo)
                else:
                    result = test(*args, **kwargs, uptane_repo=uptane_repo, image_repo=image_repo)
                return result

            if handlers and len(handlers) > 0:
                for handler in handlers:
                    result = func(handler.map(kwargs.get('test_path', '')))
                    if not result:
                        break
            else:
                result = func()
            return result
        return wrapper
    return decorator


def with_secondary(start=True, id=('secondary-hw-ID-001', str(uuid4())),
                   aktualizr_secondary_exe='src/aktualizr_secondary/aktualizr-secondary'):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, **kwargs):
            secondary = IPSecondary(aktualizr_secondary_exe=aktualizr_secondary_exe, id=id)
            if start:
                with secondary:
                    result = test(*args, **kwargs, secondary=secondary)
            else:
                result = test(*args, **kwargs, secondary=secondary)
            return result
        return wrapper
    return decorator


def with_path(paths):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, **kwargs):
            for test_path in paths:
                result = test(*args, **kwargs, test_path=test_path)
                if not result:
                    break
            return result
        return wrapper
    return decorator


class InstallManager:
    def __init__(self, aktualizr, uptane_repo, images_to_install=[]):
        self.aktualizr = aktualizr
        self.images_to_install = []
        for image in images_to_install:
            self.images_to_install.append({
                'ecu_id': image[0],
                'filename': image[1],
                'hash': uptane_repo.add_image(image[0], image[1], custom_url=image[2] if len(image) > 2 else '')
            })

    def are_images_installed(self):
        result = True
        for image in self.images_to_install:
            if not (image['hash'] == self.aktualizr.get_current_image_info(image['ecu_id'])):
                result = False
                break

        return result


def with_install_manager(default_images=True):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, aktualizr, uptane_repo, secondary=None, images_to_install=[], **kwargs):
            if default_images and (not images_to_install or len(images_to_install) == 0):
                images_to_install = [(aktualizr.id, 'primary-image.img')]
                if secondary:
                    images_to_install.append((secondary.id, 'secondary-image.img'))
            install_mngr = InstallManager(aktualizr, uptane_repo, images_to_install)
            result = test(*args, **kwargs, aktualizr=aktualizr, secondary=secondary,
                          uptane_repo=uptane_repo, install_mngr=install_mngr)
            return result
        return wrapper
    return decorator


def with_images(images_to_install):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, **kwargs):
            return test(*args, **kwargs, images_to_install=images_to_install)
        return wrapper
    return decorator


def with_customrepo(start=True, handlers=[]):
    def decorator(test):
        @wraps(test)
        def wrapper(*args, uptane_repo, **kwargs):
            def func(handler_map={}):
                custom_repo = uptane_repo.create_custom_repo(handler_map=handler_map)
                if start:
                    with custom_repo:
                        result = test(*args, **kwargs, uptane_repo=uptane_repo, custom_repo=custom_repo)
                else:
                    result = test(*args, **kwargs, uptane_repo=uptane_repo, custom_repo=custom_repo)
                return result

            if handlers and len(handlers) > 0:
                for handler in handlers:
                    result = func(handler.map(kwargs.get('test_path', '')))
                    if not result:
                        break
            else:
                result = func()
            return result
        return wrapper
    return decorator
