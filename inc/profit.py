from datetime import datetime

import tinvest

from .api import Api
from .constants import DT_FORMAT

"""
Рассчитываю все что нужно мне рассчитать
доходность, сколько кому заплачу и т.д.
!!! Это НЕ УНИВЕРСАЛЬНЫЙ расчет.
Сделан под мои задачи (без плеча, без шортов, не продаю валюту, ещё не кешился и т.д.)
:return:
"""
class Profit:
    
    def __init__(self):
        self.api = Api()
        # сортирую по времени операции
        self.usdrur = self.api.get_usdrur()
        self.currencies = self.api.get_currencies()
        self.data = self.api.data

        # СЧИТАЮ ДЕНЬГИ НА СЧЕТУ = реальные + виртуальные пролажи
        for c in self.currencies:
            # рубли
            if c.currency == tinvest.Currency.rub:
                # рублей на балансе
                self.rub_amount = c.balance
                # было продано за рубли, в т.ч. и виртуально, но без комиссий и налогов
                self.sold_for_rub = sum([op[2] for op in self.data if op[3] == 'rub'])
                # должно быть на счету после всех продаж, в т.ч. и виртуально, но без комиссий и налогов
                self.rub_amount_calculated = self.rub_amount + self.sold_for_rub
            
            # доллары (евро не будет - я с ними не работаю, но можно по аналогии)
            if c.currency == tinvest.Currency.usd:
                self.usd_amount = c.balance
                # колво купленных на бирже долл todo:Я мог бы и заводить долл на счет, но пока не актуально
                self.usd_bought = sum([op[6] for op in self.data if op[1] == 'buy' and op[4] == 'currency'])
                # бумаги проданные за долл
                self.sold_for_usd = sum([op[2] for op in self.data if op[3] == 'usd'])
                # всего долл на балансе = остатки купленных и от продаж бумаг
                self.usd_amount_calculated = self.usd_amount + self.sold_for_usd + self.usd_bought

        # СКОЛЬКО ЗАВЕЛ НА СЧЕТ, я заводил только рубли todo:Учесть ввод долл
        self.payed_in = sum([op[2] for op in self.data if op[1] == 'pay_in'])
        # todo: Учесть вывод, ещё не выводил
        # self.payed_out = sum([op[2] for op in data if op[1] == 'pay_out'])

        # ПРОДАЖА ДОЛЛАРОВ за рубли, но можно и не продавать, тогда todo:учесть вывод долл
        self.usd_sell = self.usd_amount_calculated * self.usdrur
        # self.exchange = self.usd_sell + self.rub_for_usd # todo:надо бы учитывать налоги

        # TOTAL - уже всключает все расходы (комиссии и налоги) кот указаны в таблице
        self.total = round(self.rub_amount_calculated + self.usd_sell - self.payed_in,2)

        # считаю ГОДОВУЮ ДОХОДНОСТЬ инвестиций
        # дней инвестирования
        self.period_days = (datetime.strptime(self.data[0][0], DT_FORMAT) - datetime.strptime(self.data[-1][0], DT_FORMAT)).days
        # доход в день в среднем
        self.total_day = self.total / self.period_days
        self.year_proc = round(self.total_day *100 *365 / self.payed_in, 2)


        # расходы считаю отдельно искл для визуализации
        self.taxes = sum([op[2] for op in self.data if op[1].startswith("tax")])
        self.taxes_proc = round(self.taxes * 100 / self.payed_in, 2)
        self.comissions = sum([op[2] for op in self.data if "commission" in op[1]])  # tinvest пишет commission - с двумя м ;)
        self.comissions_proc = round(self.comissions * 100 / self.payed_in, 2)

