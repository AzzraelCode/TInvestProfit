from datetime import datetime, timedelta
from operator import itemgetter

import tinvest
from tinvest import SyncClient

from inc import tcs, DT_FORMAT, COMISSION, TAX

"""
Запросы к Open API Тинькофф Инвестиций 
и сбор общего массива, в т.ч. и виртуальных продаж портфеля
"""
class Api:
    def __init__(self):
        self.tikers = {}
        self.data = []
        self.client = SyncClient(tcs.key)
        self.broker_account_id = None

        # self.broker_account_id = self.select_account()

        self.sell_portfolio()
        self.get_operations()
        self.data = sorted(self.data, key=itemgetter(0), reverse=True)

    def get_tiker_by_figi(self, figi: str) -> str:
        """
        Получаю тикер по figi и сохраняю в словарь, чтобы делать меньше запросов к апи
        :param figi:
        :return:
        """
        if figi not in self.tikers:
            self.tikers[figi] = self.client.get_market_search_by_figi(figi).payload.ticker

        return self.tikers[figi]


    def select_account(self):
        """
        Выбираю счет с кот. буду работать
        :return:
        """
        accounts = self.client.get_accounts().payload.accounts
        print("Выбери счет:")
        for index, acc in enumerate(accounts, start=1):
            print("%d - %s" % (index, acc.broker_account_type.name))
        index = input("Введи цифру: ")

        return accounts[int(index) - 1].broker_account_id


    def sell_portfolio(self):
        """
        ВИРТУАЛЬНО продаю все позиции
        :return:
        """
        resp = self.client.get_portfolio(broker_account_id=self.broker_account_id)
        dt = datetime.now()

        for pos in resp.payload.positions:
            # print(pos)

            # валюту буду суммировать и затем конвертить в рубли, позже, а поку пропускаю её вирт продажу
            if pos.instrument_type == tinvest.InstrumentType.currency: continue

            # чтобы не запрашивать стакан расчитываю ориентировочную цену продажи позиции
            # я не работаю с плечами, шортами и т.д.
            money = pos.average_position_price.value * pos.balance + pos.expected_yield.value

            t = [
                dt.strftime(DT_FORMAT),
                tinvest.OperationTypeWithCommission.sell.name,
                money,
                pos.expected_yield.currency.name,
                pos.instrument_type.name,
                pos.ticker,
                pos.balance,
                "virtual_sell",
                pos.expected_yield.value
            ]

            self.data.append(t)

            # комиссия брокера
            t = t.copy()
            t[1] = tinvest.OperationTypeWithCommission.broker_commission.name
            t[2] = round(-1 * money * COMISSION, 2)
            t[6] = 0
            t[8] = 0

            self.data.append(t)

            # если есть прибыль, то налог
            if pos.expected_yield.value > 0:
                t = t.copy()
                t[1] = tinvest.OperationTypeWithCommission.tax.name
                t[2] = round(-1 * pos.expected_yield.value * TAX, 2)
                t[6] = 0
                t[8] = 0

                self.data.append(t)


    def get_operations(self, fr=None, to=None):
        """
        Получаю операции и позиции по текущему портфелю
        :param fr:
        :param to:
        :return:
        """
        if to is None: to = datetime.now()
        if fr is None: fr = (to - timedelta(days=365))

        resp = self.client.get_operations(from_=fr, to=to, broker_account_id=self.broker_account_id)
        for op in resp.payload.operations:
            t = [
                op.date.strftime(DT_FORMAT),
                op.operation_type.name,
                op.payment,
                op.currency.name
            ]

            if op.figi:
                t.append(op.instrument_type.name)
                t.append(self.get_tiker_by_figi(op.figi))
                t.append(op.quantity_executed)

            self.data.append(t)

    def get_usdrur(self):
        """
        Курс доллара к рублю
        """
        return self.client.get_market_orderbook("BBG0013HGFT4", 1).payload.close_price  # цена доллара из стакана

    def get_currencies(self):
        """
        Кеш на аккаунте
        :return:
        """
        return  self.client.get_portfolio_currencies(broker_account_id=self.broker_account_id).payload.currencies