import logging
from typing import Dict, List, Any
from urllib.parse import urljoin

import requests
from requests import Response

from ..base_rpc import BaseRPC
from ..exceptions import TorrtRPCException
from ..utils import RPCClassesRegistry

LOGGER = logging.getLogger(__name__)


class QBittorrentRPC(BaseRPC):
    """See https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-Documentation
    for protocol spec details

    """
    alias: str = 'qbittorrent'

    api_map: dict = {
        'login': 'login',
        'api_version_path': 'version/api',
        'add_torrent': 'command/upload',
        'rem_torrent': 'command/delete',
        'rem_torrent_with_data': 'command/deletePerm',
        'get_torrent': 'query/propertiesGeneral/%s',
        'get_torrents': 'query/torrents'
    }

    headers: dict = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
    }

    torrent_fields_map: Dict[str, str] = {
        'save_path': 'download_to',
    }

    def __init__(
            self,
            url: str = None,
            host: str = 'localhost',
            port: int = 8080,
            user: str = 'admin',
            password: str = 'admin',
            enabled: bool = False
    ):
        self.cookies = {}
        self.user = user
        self.password = password
        self.enabled = enabled
        self.host = host
        self.port = port

        if url is not None:
            self.url = url

        else:
            self.url = 'http://%s:%s/' % (host, port)

    def login(self):

        try:
            data = {
                'username': self.user,
                'password': self.password
            }

            result = self.query(self.build_params('login', {'data': data}))

            if result.text != 'Ok.' or result.cookies is None:
                raise QBittorrentRPCException('Unable to auth credentials incorrect.')

            self.cookies = result.cookies

        except Exception as e:

            LOGGER.error('Failed to login using `%s` RPC: %s', self.url, str(e))
            raise QBittorrentRPCException(str(e))

    @staticmethod
    def build_params(action: str = None, params: dict = None) -> dict:

        document = {'action': action}

        if params is not None:
            document.update(params)

        return document

    def get_request_url(self, params: dict) -> str:

        key = params['action']

        url_segment = self.api_map[key]

        if 'action_params' in params:
            url_segment = url_segment % params['action_params']

        return urljoin(self.url, url_segment )

    def query(self, data: dict, files: dict = None) -> Response:

        LOGGER.debug('RPC action `%s` ...', data['action'] or 'list')

        try:
            url = self.get_request_url(data)

            request_kwargs = {}
            if self.cookies is not None:
                request_kwargs['cookies'] = self.cookies

            method = requests.get

            if 'data' in data:
                method = requests.post
                request_kwargs['data'] = data['data']

            if files is not None:
                method = requests.post
                request_kwargs['files'] = files

            try:
                response = method(url, **request_kwargs)
                if response.status_code != 200:
                    raise QBittorrentRPCException(response.text.strip())

            except Exception as e:

                LOGGER.error('Failed to query RPC `%s`: %s', url, e)
                raise QBittorrentRPCException(e)

        except Exception as e:

            LOGGER.error('Failed to query RPC `%s`: %s', data['action'], e)
            raise QBittorrentRPCException(str(e))

        return response

    def auth_query(self, data: dict, files: dict = None):

        if not self.cookies:
            self.login()

        return self.query(data, files)

    def auth_query_json(self, data: dict, files: dict = None) -> dict:

        if not self.cookies:
            self.login()

        response = self.query(data, files)

        return response.json()

    def method_get_torrents(self, hashes: List[str] = None) -> List[dict]:

        result = self.auth_query_json(self.build_params('get_torrents', {'reverse': 'true'}))

        torrents_info = []

        for torrent_data in result:
            self.normalize_field_names(torrent_data)

            torrent_data_hash = torrent_data['hash']

            if hashes is None or torrent_data_hash in hashes:

                # TODO: because query/torrents not return `comment` field
                addition_data = self.auth_query_json(
                    self.build_params('get_torrent', {'action_params': torrent_data_hash})
                )
                self.normalize_field_names(addition_data)

                torrents_info.append({
                    'hash': torrent_data_hash,
                    'name': torrent_data['name'],
                    'download_to': torrent_data['download_to'],
                    'comment' : addition_data['comment']
                })

        return torrents_info

    def method_add_torrent(self, torrent: dict, download_to: str = None, params: dict = None) -> Any:

        file_data = {'torrents': torrent['torrent']}

        if download_to is not None:
            file_data.update({'savepath': download_to})

        return self.auth_query(self.build_params(action='add_torrent'), file_data)

    def method_remove_torrent(self, hash_str: str, with_data: bool = False) -> Any:

        action = 'rem_torrent'

        if with_data:
            action = 'rem_torrent_with_data'

        data = {'hashes': hash_str}

        return self.auth_query(self.build_params(action, {'data': data}))

    def method_get_version(self) -> str:
        result = self.auth_query(self.build_params(action='api_version_path'))
        return result.text


class QBittorrentRPCException(TorrtRPCException):
    """"""


RPCClassesRegistry.add(QBittorrentRPC)
