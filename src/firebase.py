import asyncio
from datetime import datetime, timedelta
import signal
import threading
import time
import firebase_admin
from firebase_admin import credentials, db
from data_classes import Order, Heartbeat
from globals import *
from logger import logger, logging
from utils import get_private_ip, get_public_ip, get_ngrok_tunnel, update_and_reboot
from os import getenv



class FirebaseManager:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            logger.debug("Creating new instance of FirebaseManager")
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            logger.debug("Initializing FirebaseManager")
            self.initialized = True
            self.dbUrl = 'https://bintrader-ffeeb-default-rtdb.firebaseio.com/'
            self.listeners = []
            self.threads = []
            self.cached_profit = 0.0
            self.last_profit_update = None
            self.profit_update_interval = timedelta(hours=1)

            try:
                firebase_key_path = getenv(FIREBASE_KEY_PATH)

                if not firebase_key_path:
                    raise ValueError("Firebase key path are missing. Please check that they are set in environment variables.")

                self.cred = credentials.Certificate(firebase_key_path)

                firebase_admin.initialize_app(self.cred)
                logger.debug("Firebase initialized successfully.")

                logger.debug("Private and public ips was set successfully")
                self.save_ips_to_firebase()

                self.ref = db.reference(DATABASE_PATH, url=self.dbUrl)
                logger.debug("Firebase database reference set successfully.")

            except FileNotFoundError as e:
                logger.error("Firebase credentials file not found.")
                raise ValueError(f"Failed to initialize Firebase: {str(e)}")

            except Exception as e:
                logger.exception("An unexpected error occurred during Firebase initialization.")
                raise ValueError(f"Failed to initialize Firebase: {str(e)}")

    def setup_firebase(self, loop):
        self.setup_signal_handler(loop)
        self.start_listener_in_thread()

    def update_profit(self, profit: float):
        ref_profit = db.reference(PROFIT_PATH, url=self.dbUrl)
        ref_profit.set(profit)

    def send_heartbeat(self, version, status="OK"):
        heartbeat = Heartbeat.create_heartbeat(status=status, version=version)
        self.calculate_and_cache_profit()

        heartbeat_data = {
            TIMESTAMP: heartbeat.timestamp.isoformat().replace("T"," | "),
            STATUS: heartbeat.status,
            "version": heartbeat.version,
            "cpu_load": heartbeat.cpu_load,
            "memory_usage": heartbeat.memory_usage,
            "profit" : self.cached_profit
        }

        self.ref = db.reference(HEARTBEAT_PATH, url=self.dbUrl)
        self.ref.set(heartbeat_data)

    def add_order_to_firebase(self, order: Order):
        """
        Adds an order to Firebase Realtime Database if it doesn't already exist, 
        or updates it if the status or other attributes have changed.

        Parameters:
            order (Order): The order object to be added or updated.
        """
        try:
            self.ref = db.reference(ORDERS_PATH + '/' + str(order.order_id), url=self.dbUrl)

            existing_order = self.ref.get()

            if existing_order is not None:
                if existing_order[STATUS] != order.status:
                    self.ref.update({STATUS: order.status})
                    logger.info(f"Order with ID {order.order_id} updated in Firebase (status changed from "
                                f"{existing_order[STATUS]} to {order.status}).")
                else:
                    logger.debug(f"Order with ID {order.order_id} already exists in Firebase with the same status.")
            else:
                self.ref.set(order.to_dict())
                logger.info(f"Order with ID {order.order_id} added successfully to Firebase.")
        except Exception as e:
            logger.exception(f"Failed to add or update order in Firebase: {e}")

    def save_ips_to_firebase(self):
        """
        Adds public and private IP to Firebase Realtime Database.
        Updates the values if they already exist.
        """
        try:
            # Firebase references for public and private IPs
            public_ip_ref = db.reference(f"/CryptoTrading/Config/IPs/Public", url=self.dbUrl)
            private_ip_ref = db.reference(f"/CryptoTrading/Config/IPs/Private", url=self.dbUrl)
            ngrok_tunnel_ref = db.reference(f"/CryptoTrading/Config/IPs/TCPTunnel", url=self.dbUrl)

            # Get and save IPs
            public_ip = get_public_ip()
            private_ip = get_private_ip()
            ngrok_tunnel = get_ngrok_tunnel()

            public_ip_ref.set(public_ip)
            private_ip_ref.set(private_ip)
            ngrok_tunnel_ref.set(ngrok_tunnel)

            logger.info(f"Public IP ({public_ip})")
            logger.info(f"Private IP ({private_ip})")
            logger.info(f"TCP Tunnel{ngrok_tunnel} saved successfully to Firebase.")
        except Exception as e:
            logger.exception(f"Failed to save or update IPs in Firebase: {e}")

    def calculate_total_profit(self) -> float:
        """
        Calculates the total profit from orders in Firebase Realtime Database 
        with status 'FILLED' and side 'BUY'.

        Returns:
            float: Total profit from matching orders.
        """
        try:
            ref = db.reference(ORDERS_PATH, url=self.dbUrl)
            orders = ref.get()

            if not orders:
                logger.info("No orders in database.")
                return 0.0

            total_profit = 0.0
            for order_id, order in orders.items():
                if order.get(STATUS) == FILLED and order.get(ORDER_TYPE) == BUY and order.get(PROFIT) != None:
                    logger.debug(f"Order: {order}")
                    total_profit += float(order.get(PROFIT))

            return total_profit

        except Exception as e:
            logger.exception(f"Error while calculating total profit: {e}")
            return 0.0

    def calculate_and_cache_profit(self):
        """
        Updates the gain in the buffer if time has passed since the last update.
        """
        now = datetime.now()
        if self.last_profit_update is None or (now - self.last_profit_update) >= self.profit_update_interval:
            logger.info("Calculating and caching total profit.")
            self.cached_profit = self.calculate_total_profit()
            self.last_profit_update = now
        else:
            logger.debug("Using cached profit value.")

    async def shutdown(self, loop):
        """Closes active tasks and closes the loop safely."""
        logger.info("Shutting down tasks and closing listeners...")
        self.close_listeners()

        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()

        logger.info(f"Cancelling {len(tasks)} tasks...")
        await asyncio.gather(*tasks, return_exceptions=True)
        loop.stop()

    def setup_signal_handler(self, loop):
        """Sets the handling of the Ctrl+C signal."""
        def signal_handler(sig, frame):
            logger.info(f"Signal {sig} received. Shutting down...")
            asyncio.ensure_future(self.shutdown(loop))
        signal.signal(signal.SIGINT, signal_handler)

    def monitor_variable(self, path: str, listener):
            ref = db.reference(path, url=self.dbUrl)
            self.listeners.append(ref.listen(listener))

    def close_listeners(self):
        """Closes Firebase listeners and waits for threads to terminate.."""
        for listener in self.listeners:
            start_time = time.time()
            listener.close()
            logger.debug(f"Listener {listener} closed in {time.time() - start_time:.2f} seconds.")
        for thread in self.threads:
            thread.join()
        logger.debug("Firebase listeners closed.")

    def start_listener_in_thread(self):
        """Runs listeners in separate threads."""
        thread1 = threading.Thread(target=self.monitor_variable, args=(LOGGING_VARIABLE_PATH, self.logging_level_listener), daemon=True)
        thread2 = threading.Thread(target=self.monitor_variable, args=(POWER_STATUS_PATH, self.power_status_listener), daemon=True)
        thread3 = threading.Thread(target=self.monitor_variable, args=(STRATEGIES_PATH, self.strategies_listener), daemon=True)
        thread4 = threading.Thread(target=self.monitor_variable, args=(PAIRS_PATH, self.pairs_listener), daemon=True)
        thread5 = threading.Thread(target=self.monitor_variable, args=(MONITORING_PATH, self.monitoring_buy_orders_listener), daemon=True)
        thread6 = threading.Thread(target=self.monitor_variable, args=(UPDATE_PATH, self.update_listener), daemon=True)

        self.threads.extend([thread1, thread2, thread3, thread4, thread5, thread6])
        thread1.start()
        thread2.start()
        thread3.start()
        thread4.start()
        thread5.start()
        thread6.start()

    def logging_level_listener(self, event):
        global LOGGING_LEVEL
        allowed_levels = {logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL}
        previous_level = LOGGING_LEVEL.logging_level

        if event.data in allowed_levels:
            LOGGING_LEVEL.logging_level = event.data
            logger.info(f"Changing LOGGING_LEVEL: {logging.getLevelName(LOGGING_LEVEL.logging_level)}")
            logger.setLevel(LOGGING_LEVEL.logging_level)
        else:
            logger.error(f"Invalid logging level: {event.data}. Choose one of {allowed_levels}.")

            ref = db.reference(LOGGING_VARIABLE_PATH, url=self.dbUrl)
            ref.set(previous_level)
            logger.info(f"Restored previous value of level: {logging.getLevelName(previous_level)}")

    def power_status_listener(self, event):
        global POWER_STATUS

        POWER_STATUS.power_status = event.data
        logger.info(f"Power status changed to: {POWER_STATUS.power_status}")

    def monitoring_buy_orders_listener(self, event):
        global MONITORING

        MONITORING.show_buy_orders = event.data
        logger.info(f"Show buy orders changed to: {MONITORING.show_buy_orders}")

    def strategies_listener(self, event):
        """Listener for updates in the STRATEGIES path."""
        global STRATEGIES

        path = event.path.lstrip("/")
        event_data = event.data

        if not path:
            if isinstance(event_data, dict):
                logger.info("Replacing entire strategies structure.")
                try:
                    STRATEGIES.strategies = {
                        name: TradeStrategy(name=name, **data)
                        for name, data in event_data.items()
                    }
                except TypeError as e:
                    logger.error(f"Failed to rebuild strategies: {e}")
            else:
                logger.error(f"Unexpected data structure for full path update: {event_data}")
            return

        path_parts = path.split("/")

        if len(path_parts) == 1:
            strategy_name = path_parts[0]
            if isinstance(event_data, dict):
                logger.info(f"Replacing strategy {strategy_name} with new data: {event_data}")
                try:
                    STRATEGIES.strategies[strategy_name] = TradeStrategy(name=strategy_name, **event_data)
                except TypeError as e:
                    logger.error(f"Failed to update strategy {strategy_name}: {e}")
            else:
                logger.error(f"Unexpected data for strategy {strategy_name}: {event_data}")

        elif len(path_parts) == 2:
            strategy_name, field = path_parts
            if strategy_name in STRATEGIES.strategies:
                current_strategy = STRATEGIES.strategies[strategy_name]
                if hasattr(current_strategy, field):
                    current_value = getattr(current_strategy, field)
                    if current_value != event_data:
                        logger.info(f"Updating {strategy_name}.{field} from {current_value} to {event_data}")
                        setattr(current_strategy, field, event_data)
                else:
                    logger.warning(f"Strategy {strategy_name} has no field '{field}' to update.")
            else:
                logger.warning(f"Strategy {strategy_name} not found in STRATEGIES.")

        else:
            logger.warning(f"Unhandled path format: {path}")

        logger.info(f"STRATEGIES: {STRATEGIES.strategies}")

    def pairs_listener(self, event):
        """Listener for updates in the PAIRS path."""
        global PAIRS

        path = event.path.lstrip("/")
        event_data = event.data

        if not path:
            if isinstance(event_data, dict):
                logger.info("Replacing entire pairs structure.")
                try:
                    PAIRS.pairs = {
                        pair_name: {
                            "strategy_allocation": data["strategy_allocation"],
                            "trading_percentage": data["trading_percentage"]
                        }
                        for pair_name, data in event_data.items()
                    }
                except TypeError as e:
                    logger.error(f"Failed to rebuild pairs: {e}")
            else:
                logger.error(f"Unexpected data structure for full path update: {event_data}")
            return

        path_parts = path.split("/")

        if len(path_parts) == 1:
            pair_name = path_parts[0]
            if isinstance(event_data, dict):
                logger.info(f"Replacing pair {pair_name} with new data: {event_data}")
                try:
                    PAIRS.pairs[pair_name] = {
                        "strategy_allocation": event_data.get("strategy_allocation", {}),
                        "trading_percentage": event_data.get("trading_percentage", 1)
                    }
                except TypeError as e:
                    logger.error(f"Failed to update pair {pair_name}: {e}")
            else:
                logger.error(f"Unexpected data for pair {pair_name}: {event_data}")

        elif len(path_parts) == 2:
            pair_name, field = path_parts
            if pair_name in PAIRS.pairs:
                current_pair = PAIRS.pairs[pair_name]
                if field == "strategy_allocation":
                    if isinstance(event_data, dict):
                        current_pair["strategy_allocation"] = event_data
                        logger.info(f"Updating {pair_name}.strategy_allocation to {event_data}")
                    else:
                        logger.warning(f"Invalid data for {pair_name}.strategy_allocation: {event_data}")
                elif field == "trading_percentage":
                    if isinstance(event_data, (int, float)):
                        current_pair["trading_percentage"] = event_data
                        logger.info(f"Updating {pair_name}.trading_percentage to {event_data}")
                    else:
                        logger.warning(f"Invalid data for {pair_name}.trading_percentage: {event_data}")
                else:
                    logger.warning(f"Unknown field {field} for pair {pair_name}")
            else:
                logger.warning(f"Pair {pair_name} not found in PAIRS.")

        else:
            logger.warning(f"Unhandled path format: {path}")

        logger.info(f"PAIRS: {PAIRS.pairs}")

    def update_listener(self, event):
        """
        Listener for the Update class. Reacts to changes in the update status or version from the database.

        :param event: Event containing update information. Expected to receive separate events for 'update' and 'version'.
        """
        global UPDATE

        # Check if this event is for 'update' or 'version' and update the respective attribute
        if event.path == "/update":
            # Update the `update` field
            UPDATE.update = bool(event.data)
            logger.info(f"Update flag changed: Update = {UPDATE.update}")
        elif event.path == "/version":
            # Update the `version` field
            UPDATE.version = str(event.data) if event.data else "None"
            logger.info(f"Version updated to: Version = {UPDATE.version}")
        else:
            # Log an error if the event is not for recognized paths
            logger.error(f"Unexpected path in update event: {event.path}")

        # Check if an update is required and perform the update
        if UPDATE.update:
            if UPDATE.version and UPDATE.version != "None":
                logger.info(f"Performing update to specific version: {UPDATE.version}")
                try:
                    update_and_reboot(target_version=UPDATE.version)
                except Exception as e:
                    logger.error(f"Error during update to version {UPDATE.version}: {e}", exc_info=True)
            else:
                logger.info("Performing update to the latest version.")
                try:
                    update_and_reboot()
                except Exception as e:
                    logger.error(f"Error during update to the latest version: {e}", exc_info=True)