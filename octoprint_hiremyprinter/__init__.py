# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from asyncio.log import logger

from octoprint_hiremyprinter.api_client import ApiOrderRepository, OrderStatus, ApiError
import octoprint.plugin
from octoprint.util import RepeatedTimer
import concurrent.futures
from octoprint.settings import Settings
class HireMyPrinterPlugin(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.SettingsPlugin):

    def __init__(self):
        self._poll_worker = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.uploads_dir = octoprint.settings.Settings().getBaseFolder("watched")
        self.orders = None

    def _process_pending_orders(self):
        try:
            orders = self.orders.get_pending_orders()
            for order in orders:
                order.download(self.uploads_dir)
                self.orders.update_order_status(order.id, OrderStatus.SENT)
        except ApiError:
            self._logger.info("Stopping poll worker. Issue connecting to the API", exc_info=True)
            self._stop_poll_worker()

    def _poll_orders(self):
        self._logger.debug("Trying to retrieve orders from API server")
        self._executor.submit(self._process_pending_orders)

    def _start_poll_worker(self):
        if self._poll_worker is None:
            poll_interval = self._settings.get(["poll_interval"])
            self._poll_worker = RepeatedTimer(
                poll_interval, self._poll_orders, run_first=True
            )
            self._logger.info("API server poll worker started")
            self._poll_worker.start()

    def _stop_poll_worker(self):
        self._poll_worker.cancel()

    def on_after_startup(self):
        self._logger.info("Hire My Printer enabled")
        setting = Settings()
        setting.set(['feature', 'pollWatched'], True)
        setting.save()

        api_key = self._settings.get(["api_key"])
        if api_key:
            self._logger.info("API Key found. Starting poll worker")
            if not self.orders:
                self.orders = ApiOrderRepository(api_key)
            self._start_poll_worker()
        else:
            self._logger.info("API Key not found")

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        if "api_key" in data:
            if not self.orders:
                api_key = data.get("api_key")
                self.orders = ApiOrderRepository(api_key)
            self._start_poll_worker()

    def get_settings_defaults(self):
        return {
            "server": "http://localhost:3000",
            "api_key": None,
            "poll_interval": 5
        }

    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]

    def on_shutdown(self):
        self._executor.shutdown(wait=True)

__plugin_name__ = "Hire My Printer"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = HireMyPrinterPlugin()
