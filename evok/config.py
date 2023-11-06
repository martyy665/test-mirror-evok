import logging
import os
import multiprocessing
from typing import List, Dict

from pymodbus.client import AsyncModbusTcpClient
from tornado.ioloop import IOLoop

from modbus_unipi import EvokModbusSerialClient

from modbus_slave import ModbusSlave
try:
    import owclient
except ImportError:
    pass

import yaml
from devices import *

# from neuron import WiFiAdapter

try:
    import unipig
    from apigpio import I2cBus, GpioBus
except:
    pass


class EvokConfigError(Exception):
    pass


class HWDict:
    def __init__(self, dir_paths: List[str] = None, paths: List[str] = None):
        """
        :param dir_paths: path to dir for load
        :param paths: paths to config files
        """
        self.definitions = []
        scope = list()
        if dir_paths is not None:
            for dp in dir_paths:
                scope.extend([dp + f for f in os.listdir(dp)])
        if paths is not None:
            scope.extend(paths)
        if scope is None or len(scope) == 0:
            raise ValueError(f"HWDict: no scope!")
        for file_path in scope:
            if file_path.endswith(".yaml"):
                with open(file_path, 'r') as yfile:
                    ydata = yaml.load(yfile, Loader=yaml.SafeLoader)
                    if ydata is None:
                        logger.warning(f"Empty Definition file '{file_path}'! skipping...")
                        continue
                    self.definitions.append(ydata)
                    logger.info(f"YAML Definition loaded: {file_path}, type: {len(self.definitions[-1])}, "
                                f"definition count {len(self.definitions) - 1}")


class OWBusDevice:
    def __init__(self, bus_driver, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = bus_driver.circuit

    def full(self):
        return self.bus_driver.full()


class OWSensorDevice:
    def __init__(self, sensor_dev, dev_id):
        self.dev_id = dev_id
        self.sensor_dev = sensor_dev
        self.circuit = sensor_dev.circuit

    def full(self):
        return self.sensor_dev.full()


class TcpBusDevice:
    def __init__(self, circuit: str, bus_driver: AsyncModbusTcpClient, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = circuit

    def switch_to_async(self, loop: IOLoop):
        loop.add_callback(lambda: self.bus_driver.connect())


class SerialBusDevice:
    def __init__(self, circuit: str,  bus_driver: EvokModbusSerialClient, dev_id):
        self.dev_id = dev_id
        self.bus_driver = bus_driver
        self.circuit = circuit

    def switch_to_async(self, loop: IOLoop):
        loop.add_callback(lambda: self.bus_driver.connect())


class EvokConfig:

    def __init__(self, conf_dir_path: str):
        data = self.__get_final_conf(conf_dir_path=conf_dir_path)
        self.main: dict = self.__get_main_conf(data)
        self.hw_tree: dict = self.__get_hw_tree(data)

    @staticmethod
    def __get_final_conf(conf_dir_path) -> dict:
        files = os.listdir(conf_dir_path)
        if 'config.yaml' not in files:
            raise EvokConfigError(f"Missing 'config.yaml' in evok configuration directory ({conf_dir_path})")
        scope = [conf_dir_path+'/config.yaml']
        final_conf = {}
        for path in scope:
            with open(path, 'r') as f:
                ydata: dict = yaml.load(f, Loader=yaml.Loader)
            for name, value in ydata.items():
                final_conf[name] = value  # TODO: zahloubeni (neztracet data, pouze expandovat)
        return final_conf

    @staticmethod
    def __get_main_conf(data: dict) -> dict:
        ret = {}
        for name, value in data.items():
            if name not in ['hw_tree']:
                ret[name] = value
        return ret

    @staticmethod
    def __get_hw_tree(data: dict) -> dict:
        ret = {}
        if 'hw_tree' not in data:
            logger.warning("Section 'hw_tree' not in configuration!")
            return ret
        for name, value in data['hw_tree'].items():
            ret[name] = value
        return ret

    def configtojson(self):
        return self.main  # TODO: zkontrolovat!!

    def getintdef(self, key, default):
        try:
            return int(self.main[key])
        except:
            return default

    def getfloatdef(self, key, default):
        try:
            return float(self.main[key])
        except:
            return default

    def getbooldef(self, key, default):
        try:
            return bool(self.main[key])
        except:
            return default

    def getstringdef(self, key, default):
        try:
            return str(self.main[key])
        except:
            return default

    def get_hw_tree(self) -> dict:
        return self.hw_tree


def hexint(value):
    if value.startswith('0x'):
        return int(value[2:], 16)
    return int(value)


def create_devices(evok_config: EvokConfig, hw_dict):
    dev_counter = 0
    for bus_name, bus_data in evok_config.get_hw_tree().items():
        bus_data: dict
        if not bus_data.get("enabled", True):
            logger.info(f"Skipping disabled bus '{bus_name}'")
            continue
        bus_type = bus_data['type']

        bus = None
        if bus_type == 'OWBUS':
            dev_counter += 1
            bus = bus_data.get("dev_path")
            interval = bus_data.get("interval")
            scan_interval = bus_data.get("scan_interval")
            result_pipe = multiprocessing.Pipe()
            task_pipe = multiprocessing.Pipe()

            circuit = bus_name
            ow_bus_driver = owclient.OwBusDriver(circuit, task_pipe, result_pipe, bus=bus,
                                                 interval=interval, scan_interval=scan_interval)
            bus = OWBusDevice(ow_bus_driver, dev_id=dev_counter)
            Devices.register_device(OWBUS, bus)

        elif bus_type == 'MODBUSTCP':
            dev_counter += 1
            modbus_server = bus_data.get("hostname", "127.0.0.1")
            modbus_port = bus_data.get("port", 502)
            bus_driver = AsyncModbusTcpClient(host=modbus_server, port=modbus_port)
            bus = TcpBusDevice(circuit=bus_name, bus_driver=bus_driver, dev_id=dev_counter)
            Devices.register_device(TCPBUS, bus)

        elif bus_type == "MODBUSRTU":
            dev_counter += 1
            serial_port = bus_data["port"]
            serial_baud_rate = bus_data.get("baudrate", 19200)
            serial_parity = bus_data.get("parity", 'N')
            serial_stopbits = bus_data.get("stopbits", 1)
            bus_driver = EvokModbusSerialClient(port=serial_port, baudrate=serial_baud_rate, parity=serial_parity,
                                                stopbits=serial_stopbits, timeout=1)
            bus = SerialBusDevice(circuit=bus_name, bus_driver=bus_driver, dev_id=dev_counter)
            Devices.register_device(SERIALBUS, bus)

        if 'devices' not in bus_data:
            logging.info(f"Creating bus '{bus_name}' with type '{bus_type}'.")
            continue

        logging.info(f"Creating bus '{bus_name}' with type '{bus_type}' with devices.")
        for device_name, device_data in bus_data['devices'].items():
            if not device_data.get("enabled", True):
                logger.info(f"^ Skipping disabled device '{device_name}'")
                continue
            logging.info(f"^ Creating device '{device_name}' with type '{bus_type}'")
            try:
                dev_counter += 1
                if bus_type == 'OWBUS':
                    ow_type = device_data.get("type")
                    address = device_data.get("address")
                    interval = device_data.getintdef("interval", 15)

                    circuit = device_name
                    sensor = owclient.MySensorFabric(address, ow_type, bus, interval=interval, circuit=circuit,
                                                     is_static=True)
                    if ow_type in ["DS2408", "DS2406", "DS2404", "DS2413"]:
                        sensor = OWSensorDevice(sensor, dev_id=dev_counter)
                    Devices.register_device(SENSOR, sensor)

                elif bus_type in ['MODBUSTCP', 'MODBUSRTU']:
                    slave_id = device_data.get("slave-id", 1)
                    scanfreq = device_data.get("scan_frequency", 1)
                    scan_enabled = device_data.get("scan_enabled", True)
                    device_model = device_data["model"]
                    circuit = device_name
                    major_group = device_name

                    slave = ModbusSlave(bus, circuit, evok_config, scanfreq, scan_enabled,
                                        hw_dict, device_model=device_model, slave_id=slave_id,
                                        dev_id=dev_counter, major_group=major_group)
                    Devices.register_device(MODBUS_SLAVE, slave)

                else:
                    dev_counter -= 1
                    logger.error(f"Unknown bus type: '{bus_type}'! skipping...")

            except Exception as E:
                logger.exception(f"Error in config section '{bus_type}:{device_name}' - {str(E)}")


def add_aliases(alias_conf):
    if alias_conf is not None:
        for alias_conf_single in alias_conf:
            if alias_conf_single is not None:
                if "version" in alias_conf_single and "aliases" in alias_conf_single and alias_conf_single[
                    "version"] == 1.0:
                    for dev_pointer in alias_conf_single['aliases']:
                        try:
                            dev_obj = Devices.by_int(dev_pointer["dev_type"], dev_pointer["circuit"])
                            logger.info("Alias loaded: " + str(dev_obj) + " " + str(dev_pointer["name"]))
                            if Devices.add_alias(dev_pointer["name"], dev_obj):
                                dev_obj.alias = dev_pointer["name"]
                        except Exception as E:
                            logger.exception(str(E))


def add_wifi():
    wifi = WiFiAdapter("1_01")
    Devices.register_device(WIFI, wifi)
