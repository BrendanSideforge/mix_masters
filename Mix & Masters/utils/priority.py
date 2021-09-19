
class Priority:
    def __init__(
        self,
        bot,
        ticket_information: dict,
        referrals: int,
        previous_transactions: int,
        price: int,
        addons: dict
    ):
        self.bot = bot
        self.ticket_information = ticket_information
        self.referrals = referrals
        self.previous_transactions = previous_transactions
        self.price = price
        self.addons = addons
        self.total_points = self.price

        # weights
        self.referral_weight = 10
        self.previous_transaction_weight = 5
        # price weight is the price, its the baseline of points
        # each addon has a weight of its price

        # start weighing attributes
        self._weight_points()

    def _determine_referral_points(self):

        self.total_points += self.referrals * self.referral_weight

    def _determine_previous_transactions_points(self):
        
        self.total_points += self.previous_transactions * self.previous_transaction_weight

    def _determine_addon_points(self):

        # go through each addon and add the price of it to the points
        for addon in self.addons:
            found_order_addons = [order_addon for order_addon in self.bot.config['order_addons'] if order_addon['name'] == addon]
            self.total_points += found_order_addons[0]['value']

    def _weight_points(self):

        self._determine_referral_points()
        self._determine_previous_transactions_points()
        self._determine_addon_points()


    
