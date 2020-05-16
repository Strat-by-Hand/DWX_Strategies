# -*- coding: utf-8 -*-
"""
    coin_flip_traders.py
    
    An example trading strategy created using the Darwinex ZeroMQ Connector
    for Python 3 and MetaTrader 4.
    
    Source code:
    https://github.com/darwinex/DarwinexLabs/tree/master/tools/dwx_zeromq_connector
    
    The strategy launches 'n' threads (each representing a trader responsible
    for trading one instrument)
    
    Each trader must:
        
        1) Execute a maximum of 1 trade at any given time.
        
        2) Close existing trades after they have been in execution for 
           5 seconds.    
           
        3) Flip a coin - random.randombits(1) - to decide on a BUY or SELL
        
        4) Keep trading until the market is closed (_market_open = False)
    --
    
    @author: Darwinex Labs (www.darwinex.com)
    
    Copyright (c) 2019 onwards, Darwinex. All rights reserved.
    
    Licensed under the BSD 3-Clause License, you may not use this file except 
    in compliance with the License. 
    
    You may obtain a copy of the License at:    
    https://opensource.org/licenses/BSD-3-Clause
"""


#############################################################################
#############################################################################

#############################################################################
#############################################################################

from base.DWX_ZMQ_Strategy import DWX_ZMQ_Strategy

from pandas import Timedelta
from threading import Thread, Lock
from time import sleep
from datetime import datetime

class scalper_trader(DWX_ZMQ_Strategy):
    
    def __init__(self, _name="COIN_FLIP_TRADERS",
                 _symbols=[('EURUSD',0.01)],
                 _delay=0.1,
                 _broker_gmt=3,
                 _verbose=False, 
                 _max_trades=2,
                 _close_t_delta=5):
        
        super().__init__(_name,
                         _symbols,
                         _broker_gmt,
                         _verbose)
        
        # This strategy's variables
        self._traders = []
        self._strike_amount = 10    
        self._market_open = True
        self._max_trades = _max_trades
        self._close_t_delta = _close_t_delta
        self._delay = _delay
        self._verbose = _verbose
        
        # lock for acquire/release of ZeroMQ connector
        self._lock = Lock()
        
    ##########################################################################
    
    def _run_(self):
        
        """
        Logic:
            
            For each symbol in self._symbols:
                
                1) Open a new Market Order every 2 seconds
                2) Close any orders that have been running for 10 seconds
                3) Calculate Open P&L every second
                4) Plot Open P&L in real-time
                5) Lot size per trade = 0.01
                6) SL/TP = 10 pips each
        """
        
        # Launch traders!
        for _symbol in self._symbols:
            
            _t = Thread(name="{}_Trader".format(_symbol[0]),
                        target=self._trader_, args=(_symbol,self._max_trades))
            
            _t.daemon = True
            _t.start()
            
            print('[{}_Trader] Alright, here we go.. Gerrrronimooooooooooo!  ..... xD'.format(_symbol[0]))
            
            self._traders.append(_t)
        
        print('\n\n+--------------+\n+ LIVE UPDATES +\n+--------------+\n')
        
        # _verbose can print too much information.. so let's start a thread
        # that prints an update for instructions flowing through ZeroMQ
        self._updater_ = Thread(name='Live_Updater',
                               target=self._updater_,
                               args=(self._delay,))
        
        self._updater_.daemon = True
        self._updater_.start()
        
    ##########################################################################
    
    def _updater_(self, _delay=0.1):
        
        while self._market_open:
            
            try:
                # Acquire lock
                self._lock.acquire()
                
                print('\r{}'.format(str(self._zmq._get_response_())), end='', flush=True)
                
            finally:
                # Release lock
                self._lock.release()
        
            sleep(self._delay)
            
    ##########################################################################
    
    def _trader_(self, _symbol, _max_trades):
        
        # Note: Just for this example, only the Order Type is dynamic.
        
        #construct first order form
        _default_order_1 = self._zmq._generate_default_order_dict()
        _default_order_1['_type'] = 4
        _default_order_1['_symbol'] = _symbol[0]
        _default_order_1['_lots'] = _symbol[1]
        _default_order_1['_SL'] = _default_order_1['_TP'] = 120
        _default_order_1['_comment'] = '{}_Trader'.format(_symbol[0])
        _default_order_1['_magic'] = 1
        
        #construct second order form
        _default_order_2 = self._zmq._generate_default_order_dict()
        _default_order_2['_type'] = 5
        _default_order_2['_symbol'] = _symbol[0]
        _default_order_2['_lots'] = _symbol[1]
        _default_order_2['_SL'] = _default_order_2['_TP'] = 120
        _default_order_2['_comment'] = '{}_Trader'.format(_symbol[0])
        _default_order_2['_magic'] = 2
        
        """
        Default Order:
        --
        {'_action': 'OPEN',
         '_type': 0,
         '_symbol': EURUSD,
         '_price':0.0,
         '_SL': 100,                     # 10 pips
         '_TP': 100,                     # 10 pips
         '_comment': 'EURUSD_Trader',
         '_lots': 0.01,
         '_magic': 123456}
        """
        ##############################
        # SUBSCRIBE TO MARKET PRICES #
        ##############################
        
        self._zmq._DWX_MTX_SUBSCRIBE_MARKETDATA_()
        sleep(1)       
        
        newstimepricehigh = None
        newstimepricelow = None
        buystopticket = None
        sellstopticket = None
        
        
        while self._market_open:
            
                newstime = datetime(2020,5,11,17,57)
                newstimeminus2 = newstime - Timedelta(minutes=2)
                timedifftoorder = datetime.now() - newstimeminus2
                currenttime = datetime.now()
                time_buffer = 120
                fiveminsbuffer = newstime + Timedelta(minutes=5)
            
#            try:
#                self._lock.acquire()
            
                _ot = self._reporting._get_open_trades_('{}_Trader'.format(_symbol[0]),
                                                            self._delay,
                                                            10)
                ''' if there are zero orders and current time is less than buffer seconds away from news '''
                if  _ot.shape[0] == 0 and 0 < timedifftoorder.total_seconds() < time_buffer:
                    
                        
                        #Getting current price
                        Temp_CurrBidAsk = self._zmq._Market_Data_DB['EURUSD'].items()
                        CurrBidAsk = list(Temp_CurrBidAsk)[-1][1]
                        newstimepricehigh = (CurrBidAsk[0] + CurrBidAsk[1])/2 + 0.0012
                        newstimepricelow = newstimepricehigh - 0.0024
                        
                        #setting price for order form 1
                        _default_order_1['_price'] = newstimepricehigh
                        
                        #set buy stop using order form 1
                        _ret = self._execution._execute_(_default_order_1,
                                                         self._verbose,
                                                         self._delay,
                                                         10)
                        
                        #get ticket for this buy stop
                        sleep(1)
                        buystopticket = _ret['_ticket']                     
                        
                        #setting price for order form 2
                        _default_order_2['_price'] = newstimepricelow
                        
                        #set sell stop using order form 2
                        _retto = self._execution._execute_(_default_order_2,
                                                         self._verbose,
                                                         self._delay,
                                                         10)
                        
                        #get ticket for the sell stop
                        sleep(1)
                        sellstopticket = _retto['_ticket']
                        
                        continue
                    
                    
                elif currenttime > newstime:
                    Temp_CurrBidAsk2 = self._zmq._Market_Data_DB['EURUSD'].items()                    
                    CurrBidAsk2 = list(Temp_CurrBidAsk2)[-1][1]
                    CurrBidAsk3 = list(Temp_CurrBidAsk2)[-2][1]
                    currentprice = (CurrBidAsk2[0] + CurrBidAsk2[1])/2
                    previousprice = (CurrBidAsk3[0] + CurrBidAsk3[1])/2
                    
                    if currentprice < newstimepricelow:
                        self._zmq._DWX_MTX_CLOSE_TRADE_BY_TICKET_(buystopticket)
                        
                        if currentprice < previousprice:
                            self._zmq._DWX_MTX_MODIFY_TRADE_BY_TICKET_(sellstopticket,120,10000)
                        continue
                        
                    elif currentprice > newstimepricehigh:
                        self._zmq._DWX_MTX_CLOSE_TRADE_BY_TICKET_(sellstopticket)
                        
                        if currentprice > previousprice:
                            self._zmq._DWX_MTX_MODIFY_TRADE_BY_TICKET_(buystopticket,120,10000)
                            
                        continue
                        
                    
                    elif currenttime > fiveminsbuffer:
                        self._zmq._DWX_MTX_CLOSE_ALL_TRADES_()
                        break
                    
                    else:
                        continue
                        
                        
                else:
                    
                    continue
       
#            finally:
#                self._lock.release()

            
            
    ##########################################################################  
    def _stop_(self):
        
        self._market_open = False
        
        for _t in self._traders:
        
            # Setting _market_open to False will stop each "trader" thread
            # from doing anything more. So wait for them to finish.
            _t.join()
            
            print('\n[{}] .. and that\'s a wrap! Time to head home.\n'.format(_t.getName()))
        
        # Kill the updater too        
        self._updater_.join()
        
        print('\n\n{} .. wait for me.... I\'m going home too! xD\n'.format(self._updater_.getName()))
        
        # Send mass close instruction to MetaTrader in case anything's left.
        self._zmq._DWX_MTX_CLOSE_ALL_TRADES_()
        
    ##########################################################################


a = scalper_trader()
a._run_()