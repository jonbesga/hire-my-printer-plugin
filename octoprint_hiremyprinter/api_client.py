from dataclasses import dataclass
import requests
from marshmallow import Schema, fields, post_load
import os
import enum

class OrderStatus(enum.Enum):
    PENDING = 'pending'
    SENT = 'sent'

class ApiError(Exception):
    pass

@dataclass
class ApiOrder:
    id: int
    name: str
    location: str
    status: OrderStatus

    def download(self, destination_path):
        r = requests.get(url=self.location)
        filename = os.path.join(destination_path, f'{self.name}.gcode')
        with open(filename, 'wb') as fd:
            fd.write(r.content)


class ApiOrderSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    location = fields.URL()
    status = fields.Str()

    @post_load
    def make_api_order(self, data, **kwargs):
        data = {**data, 'status': OrderStatus(data.get('status'))}
        return ApiOrder(**data)


class ApiOrderRepository:
    def __init__(self, api_key) -> None:
        self.api_client: ApiClient = ApiClient(api_key, server=os.getenv("HMP_API", 'https://hiremyprinter-fakeapi.jonbesga.com/'))

    def update_order_status(self, id, status: OrderStatus):
        self.api_client.patch(f'orders/{id}/', {"status": status.value})

    def get_pending_orders(self):
        response = self.api_client.get('orders/?status=pending')
        orders_schema = ApiOrderSchema(many=True)
        return orders_schema.loads(response.content)


class ApiClient:
    def __init__(self, api_key, server) -> None:
        self.api_key = api_key
        self.server = server

    def post(self, path, payload):
        return self._make_request(path, payload, method='POST')

    def patch(self, path, payload):
        return self._make_request(path, payload, method='PATCH')

    def get(self, path):
        return self._make_request(path, method='GET')

    def _make_request(self, path, payload=None, method='GET'):
        try:
            response = requests.request(method, f'{self.server}/{path}', json=payload, headers={
                'Authorization': f'Bearer {self.api_key}'
            })
            return response
        except requests.exceptions.ConnectionError as err:
            raise ApiError(err)
