#!/usr/bin/env python3

import time
import argparse
import logging
import signal
import sys
from configparser import RawConfigParser
import paho.mqtt.client as mqtt
import serial

serial_port = None
mqtt_client = None
topic = ''
last_line = ''

def sig_handler( signal, frame ):
    logger = logging.getLogger( 'sigint' )
    logger.info( 'closing down...' )
    if serial_port:
        serial_port.close()

    if mqtt_client:
        mqtt_client.loop_stop()
                                                
    sys.exit(0)

def on_connect( client, userdata, flags, rc ):
    logger = logging.getLogger( 'mqtt' )
    logger.info( 'connected, flags: %s, result code: %s', flags, rc )
    client.subscribe( topic )

def on_message( client, userdata, msg ):
    global last_line
    logger = logging.getLogger( 'mqtt' )
    logger.debug( 'message received at %s: %s', msg.topic, msg.payload )
    if serial_port and serial_port.is_open:
        serial_port.write( msg.payload + b'\r\n' )
        last_line = msg.payload + b'\r\n'
    else:
        logger.error( 'serial port not open!' )

def main():

    global serial_port
    global mqtt_client
    global topic

    signal.signal( signal.SIGINT, sig_handler )
    signal.signal( signal.SIGTERM, sig_handler )

    parser = argparse.ArgumentParser()

    parser.add_argument( '-c', '--config', default='/etc/mqtt2stty.ini' )

    parser.add_argument( '-s', '--serial', default='/dev/ttyACM0' )

    parser.add_argument( '-v', '--verbose', action='store_true' )

    parser.add_argument( '-b', '--baud', type=int, default=115200 )

    parser.add_argument( '-t', '--topic' )

    args = parser.parse_args()

    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    logging.basicConfig( level=level )
    logger = logging.getLogger( 'main' )

    topic = args.topic

    config = RawConfigParser()
    config.read( args.config )

    mqtt_client = mqtt.Client()
    mqtt_client.enable_logger()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.tls_set( config['mqtt']['ca'] )
    mqtt_client.username_pw_set(
        config['mqtt']['username'], config['mqtt']['password'] )
    mqtt_client.connect_async(
        config['mqtt']['host'], config.getint( 'mqtt', 'port' ) )
    mqtt_client.loop_start()

    serial_port = serial.Serial(
        args.serial, baudrate=args.baud, timeout=2.0)

    time.sleep( 0.2 )

    while True :
        line = serial_port.readline().decode( 'utf-8' ).strip()
        if 0 < len( line ):
            logger.debug( '%s: %s', args.serial, line )
            if 'reset' == line:
                serial_port.write( last_line )
                
        #if mqtt_client.is_connected():
        #    mqtt_client.publish( topic=topic, payload=line )

if '__main__' == __name__:
    main()

