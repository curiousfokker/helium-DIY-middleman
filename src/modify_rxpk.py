

"""
This is mostly a placeholder for more sophisticated modification but I want it in the flow
Things like syncronizing timestamps between multiple gateways (so timestamps appear in order) and
better mapping of input RSSI/SNR to output RSSI/SNR, etc
"""


import json
import time
import datetime as dt



class RXMetadataModification:
    def __init__(self):
        self.min_rssi = -120
        self.max_rssi = -90  # valid to 50 miles via FSPL filter
        self.max_snr = 0
        self.min_snr = -20
        self.tmst_offset = 0


    def modify_rxpk(self, rxpk, src_mac=None, dest_mac=None):
        """
        JSON object
        :param rxpk: per PUSH_DATA https://github.com/Lora-net/packet_forwarder/blob/master/PROTOCOL.TXT
        :return: object with metadata modified
        """

        # simple clipping low and high, could be a lot more sophisticated to add randomness or better mapping
        rxpk['rssi'] = min(self.max_rssi, max(self.min_rssi, rxpk['rssi']))
        rxpk['lsnr'] = min(self.max_snr,  max(self.min_snr,  rxpk['lsnr']))

        # modify tmst (Internal timestamp of "RX finished" event (32b unsigned)) to be aligned to uS since midnight UTC
        # this will be discontinuous once a day but that is basically same effect as a gateway reset / forwarder reboot
        # acceptable for proof-of-concept
        # also note 'time' is only available if there is a gps connected BUT time could be way off if there is a poor GPS fix
        # therefore compare to current time and only trust 'time' field if within 1.5s of now.  If 'time' is not available or
        # cannot be trusted, use the current time as assumed arrival time
        ts_dt = dt.datetime.utcnow()
        if 'time' in rxpk:
            ts_str = rxpk['time']
            if ts_str[-1] == 'Z':
                ts_str = ts_str[:-1]
                ts_dt = dt.datetime.fromisoformat(ts_str)
            if(abs((ts_dt - dt.datetime.utcnow()).total_seconds()) > 1.5):
                ts_dt = dt.datetime.utcnow()

        ts_midnight = dt.datetime(year=ts_dt.year, month=ts_dt.month, day=ts_dt.day, hour=0, minute=0, second=0, microsecond=0)
        elapsed_us = int((ts_dt-ts_midnight).total_seconds() * 1e6)
        elapsed_us_u32 = elapsed_us % 2**32

        #print(f"elapsed us: {elapsed_us} ({elapsed_us/1e6}s), as u32 = {elapsed_us_u32}")
        if src_mac != dest_mac:
            rxpk['tmst'] = (elapsed_us_u32 + self.tmst_offset) % 2**32
        else:
            tmst_offset = (rxpk['tmst'] - elapsed_us_u32 + 2**32) % 2**32
            #  print(f"updated tmst_offset from:{self.tmst_offset} to {tmst_offset} (error: {self.tmst_offset - tmst_offset})")
            self.tmst_offset = tmst_offset

        return rxpk
