from deltafy_xbrl.tools import *
from datetime import datetime, timedelta
from lxml import etree
import decimal


class XBRLParser(object):
    """
    Deltafy XBRL parser client
    """
    amendment_flag = None
    fiscal_year_end = None
    fiscal_period_focus = None
    fiscal_year_focus = None
    period_end_date = None
    document_type = None
    cik = None
    current_reporting_status = None
    filer_category = None
    registrant_name = None
    voluntary_filers = None
    well_known_issuer = None
    shell_company = None
    small_business = None
    trading_symbols= None
    currency = None
    instant_context = None
    duration_context = None

    def __init__(self, instance_file_path=None):
        """
        Initializes the XBRL Parser client

        Loads the instance file as an etree object and attempts to load all of
        the basic fields and contexts that are necessary to examine the filing.

        Currently loads only the current period's instant and duration contexts.
        """
        instance_data = None

        with open(instance_file_path, 'rb') as f:
            # US_ASCII encoding (for US/SEC files)
            instance_data = f.read().decode('utf-8').encode('ascii')

        try:
            self.instance_root = etree.fromstring(instance_data)
        except etree.XMLSyntaxError:    # libxml2 chokes on files > 9.5mb
            # Build a parser with libxml2's XML_PARSE_HUGE option
            p = etree.XMLParser(huge_tree=True)
            self.instance_root = etree.fromstring(instance_data, p)

        # Load namespaces
        self.ns = self.instance_root.nsmap
        if not self.ns.get('xbrli'):
            self.ns['xbrli'] = 'http://www.xbrl.org/2003/instance'
        if not self.ns.get('xlmns'):
            self.ns['xlmns'] = 'http://www.xbrl.org/2003/instance'

        try:
            # If there is an empty namespace, it will break XPath queries
            del self.ns[None]
        except KeyError:
            pass

        # Load Document & Entity Information
        dei_nodes = self.instance_root.xpath(
            './/dei:*[@contextRef]', 
            namespaces=self.ns
        )
        self.assign_dei_fields(dei_nodes)

        # Load contexts, currency, balance sheet date
        self.get_balance_sheet_date()
        self.get_current_instant_context()
        self.get_current_duration_context()
        self.retrieve_currency()

        # Try to fix any errors that prevented correct loading
        self.monkey_patch(instance_file_path)

    def assign_dei_fields(self, dei_nodes):
        """
        Maps some common Document and Entity Information fields
        """
        truth_values = ['yes', 'true']
        for node in dei_nodes:

            # dei:AmendmentFlag
            if 'AmendmentFlag' in node.tag:
                if node.text.lower() in truth_values:
                    self.amendment_flag = True
                else:
                    self.amendment_flag = False

            # dei:CurrentFiscalYearEndDate
            elif 'CurrentFiscalYearEndDate' in node.tag:
                self.fiscal_year_end = node.text

            # dei:DocumentFiscalPeriodFocus
            elif 'DocumentFiscalPeriodFocus' in node.tag:
                self.fiscal_period_focus = node.text

            # dei:DocumentFiscalYearFocus
            elif 'DocumentFiscalYearFocus' in node.tag:
                self.fiscal_year_focus = int(node.text)

            # dei:DocumentPeriodEndDate
            elif 'DocumentPeriodEndDate' in node.tag:
                self.period_end_date = datetime.strptime(
                    node.text, '%Y-%m-%d'
                )

            # dei:DocumentType
            elif 'DocumentType' in node.tag:
                self.document_type = node.text

            # dei:EntityCentralIndexKey
            elif 'EntityCentralIndexKey' in node.tag:
                self.cik = node.text

            # dei:EntityCurrentReportingStatus
            elif 'EntityCurrentReportingStatus' in node.tag:
                if node.text.lower() in truth_values:
                    self.current_reporting_status = True
                else:
                    self.current_reporting_status = False

            # dei:EntityFilerCategory
            elif 'EntityFilerCategory' in node.tag:
                self.filer_category = node.text

            # dei:EntityRegistrantName
            elif 'EntityRegistrantName' in node.tag:
                self.registrant_name = node.text

            # dei:EntityVoluntaryFilers
            elif 'EntityVoluntaryFilers' in node.tag:
                if node.text.lower() in truth_values:
                    self.voluntary_filers = True
                else:
                    self.voluntary_filers = False

            # dei:EntityWellKnownSeasonedIssuer
            elif 'EntityWellKnownSeasonedIssuer' in node.tag:
                if node.text.lower() in truth_values:
                    self.well_known_issuer = True
                else:
                    self.well_known_issuer = False

            # dei:EntityShellCompany
            elif 'EntityShellCompany' in node.tag:
                if node.text.lower() in truth_values:
                    self.shell_company = True
                else:
                    self.shell_company = False

            # dei:EntitySmallBusiness
            elif 'EntitySmallBusiness' in node.tag:
                if node.text.lower() in truth_values:
                    self.small_business = True
                else:
                    self.small_business = False

            # dei:TradingSymbol
            elif 'TradingSymbol' in node.tag:
                self.trading_symbols= [x for x in node.text.split(", ")]

    def get_balance_sheet_date(self):
        """
        Assigns a filing's balance sheet date to the parser instance

        Starts by using the document period end date, then attempts to confirm that
        this is correct by using data in the instant context nodes
        """
        end_date = self.period_end_date.strftime('%Y-%m-%d')
        bs_date = end_date

        # Try to confirm by finding an instant context with end_date
        xpath = "//xlmns:context[not(.//xlmns:segment) " + \
                "and xlmns:period/xlmns:instant[normalize-space() " + \
                "= '{0}']]".format(end_date)

        results = self.instance_root.xpath(xpath, namespaces=self.ns)

        if not len(results):
            # Get ALL of the instant context nodes as a back-up plan
            xpath = "//xlmns:context[not(.//xlmns:segment) " + \
                    "and xlmns:period/xlmns:instant]"
            all_instants = self.instance_root.xpath(xpath, namespaces=self.ns)

            if len(all_instants):
                # Now try to find something CLOSE to end_date
                closest_instant = None
                fewest_days = 365
                for node in all_instants:
                    instant_string = node.xpath(
                        "xlmns:period/xlmns:instant/text()",
                        namespaces=self.ns
                    )
                    instant_date = strip_newlines(instant_string[0])
                    days_apart = delta_days(instant_date, end_date)
                    if days_apart < closest_instant['days_from_dei_end']:
                        closest_instant = instant_date
                        fewest_days = days_apart
                bs_date = closest_instant['date']
            else:
                # By some error, the filing has no instance contexts at all
                pass

        self.balance_sheet_date = datetime.strptime(bs_date, '%Y-%m-%d')

    def get_current_instant_context(self):
        """
        Assigns the current fiscal period's instant context for the XBRL filing

        Searches context nodes for a dimensionless entry (no 'segment'
        descendent nodes) where the 'period' child-node has an 'instance'
        child-node with an end date matching the document period end date.

        Note: the 'instant' of balance sheet concepts is usually the last day of
        the fiscal period (end date), but very occasionally it is not.
        """
        end_date = self.period_end_date.strftime('%Y-%m-%d')

        xpath = "//xlmns:context[not(.//xlmns:segment) and " + \
                "xlmns:period/xlmns:instant[normalize-space() " + \
                "= '{0}']]".format(end_date)

        instant_nodes = self.instance_root.xpath(xpath, namespaces=self.ns)
        if not len(instant_nodes):
            # Try balance sheet date instead (sometimes different from end date)
            xpath = "//xlmns:context[not(.//xlmns:segment) " + \
                    "and xlmns:period/xlmns:instant[normalize-space() " + \
                    "= '{0}']]".format(self.balance_sheet_date)

            instant_nodes = self.instance_root.xpath(
                xpath, 
                namespaces=self.ns
            )

        if len(instant_nodes) == 1:
            self.instant_context = instant_nodes[0].attrib['id']

    def get_current_duration_context(self):
        """
        Assigns the current duration context for XBRL filings

        Searches context nodes for dimensionless entries (no 'segment'
        descendent nodes) where the 'period' child-node has an 'endDate'
        that matches the period end date and an appropriate 'startDate'.
        
        For 10-K (full year) filings, an appropriate 'startDate' should 
        be one year before end date. For 10-Q (quarterly) filings, an
        appropriate 'startDate' should be greater than 60 days but less
        than 120 days before the end date.

        **This also sets the document period start date as a side-effect,
        because it is defined only in duration context nodes, not DEI
        nodes (as if that's not ridiculous)
        """
        end_date = self.period_end_date.strftime('%Y-%m-%d')
        xpath = "//xlmns:context[not(.//xlmns:segment) " + \
                "and xlmns:period/xlmns:endDate[normalize-space() " + \
                "= '{0}']]".format(end_date)

        duration_nodes = self.instance_root.xpath(xpath, namespaces=self.ns)

        if not len(duration_nodes):
            # Try using balance sheet date as a backup
            xpath = "//xlmns:context[not(.//xlmns:segment) " + \
                    "and xlmns:period/xlmns:endDate[normalize-space() " + \
                    "= '{0}']]".format(self.balance_sheet_date)
            duration_nodes = self.instance_root.xpath(
                xpath, 
                namespaces=self.ns
            )

        if len(duration_nodes):
            i = 0
            while i < len(duration_nodes) and self.duration_context == None:
                start_date = strip_newlines(duration_nodes[i].xpath(
                    "xlmns:period/xlmns:startDate/text()",
                    namespaces=self.ns
                )[0])

                if self.document_type == "10-Q":
                    # The duration should be one quarter
                    days = delta_days(start_date, end_date)
                    if days > 60 and days < 120:
                        self.duration_context = duration_nodes[i].attrib['id']
                        self.period_start_date = datetime.strptime(
                            start_date,
                            '%Y-%m-%d'
                        )
                       
                elif self.document_type == "10-K":
                    # The duration should be a full year
                    if full_year_period(start_date, end_date):
                        self.duration_context = duration_nodes[i].attrib['id']
                        self.period_start_date = datetime.strptime(
                            start_date,
                            '%Y-%m-%d'
                        )
                i += 1
            
            # If no 10-K duration is full-year, co. maybe changing their fiscal year
            if self.document_type == "10-K" and not self.duration_context:
                # Find the matching duration representing the longest period
                i = 0
                longest_duration = {
                    'id': '',
                    'start_date': '',
                    'total_months': '',
                }
                while i < len(duration_nodes):
                    start_date = strip_newlines(duration_nodes[i].xpath(
                        "xlmns:period/xlmns:startDate/text()",
                        namespaces=self.ns,
                    )[0])
                    total_months = count_months(start_date, end_date)
                    if total_months > longest_duration['total_months']:
                        longest_duration['id'] = duration_nodes[i].attrib['id']
                        longest_duration['start_date'] = start_date
                        longest_duration['total_months'] = total_months
                    i += 1
                    self.duration_context = longest_duration['id']
                    self.period_start_date = datetime.strptime(
                        longest_duration['start_date'],
                        '%Y-%m-%d',
                    )

    def extract_year_from_period_end_date(self):
        """
        Failover method to determine a filing's fiscal year focus
        """
        focus_year = None
        if self.period_end_date:
            end_month = self.period_end_date.month
            end_year = self.period_end_date.year
            if end_month > 6:
                # More than half the year was in the end-year
                focus_year = end_year
            else:
                # Most of the year was (probably) the previous year
                focus_year = end_year - 1

    def decode_units(self, unit_tag):
        """
        Translates fact unitRefs into unit measure definitions
        """
        unit_measure = "not specified"
        unit_xpath = "//xlmns:unit[@id='{id}']".format(id=unit_tag)
        unit_nodes = self.instance_root.xpath(
            unit_xpath, 
            namespaces=self.ns,
        )

        if len(unit_nodes):
            child_nodes = unit_nodes[0].getchildren()
            if "measure" in child_nodes[0].tag:
                unit_measure = child_nodes[0].text
                if "iso4217:" in unit_measure:
                    unit_measure = unit_measure.split(":")[-1].lower()

        return unit_measure

    def retrieve_currency(self):
        """
        Assigns the filing's currency by testing some balance sheet concepts
        """
        currency = "not specified"
        common_bs_concepts = [
            'us-gaap:Assets',
            'us-gaap:AssetsCurrent',
            'us-gaap:AssetsNoncurrent',
            'us-gaap:CashAndCashEquivalentsAtCarryingValue',
            'us-gaap:Cash',
            'us-gaap:CashAndDueFromBanks',
            'us-gaap:CashCashEquivalentsAndShortTermInvestments',
            'us-gaap:ShortTermInvestments',
            'us-gaap:MarketableSecuritiesCurrent',
            'us-gaap:AvailableForSaleSecuritiesCurrent',
            'us-gaap:CashEquivalentsAtCarryingValue',
            'us-gaap:OtherShortTermInvestments',
            'us-gaap:TradingSecurities',
            'us-gaap:TradingSecuritiesCurrent',
            'us-gaap:AccountsNotesAndLoansReceivableNetCurrent',
            'us-gaap:AccountsReceivableNetCurrent',
            'us-gaap:AccountsReceivableNet',
            'us-gaap:NontradeReceivablesCurrent',
            'us-gaap:NotesAndLoansReceivableNetCurrent',
            'us-gaap:NotesReceivableNet', 
            'us-gaap:OtherReceivablesNetCurrent', 
            'us-gaap:PremiumsAndOtherReceivablesNet',
            'us-gaap:OtherReceivables',
            'us-gaap:ReceivablesNetCurrent',
            'us-gaap:InventoryNet',
            'us-gaap:InventoryFinishedGoodsNetOfReserves',
            'us-gaap:InventoryFinishedGoodsAndWorkInProgress',
            'us-gaap:Goodwill',
            'us-gaap:PropertyPlantAndEquipmentNet', 
            'us-gaap:AccountsPayableCurrent',
            'us-gaap:AccountsPayableCurrentAndNoncurrent', 
            'us-gaap:ShortTermBorrowings', 
            'us-gaap:CommercialPaper',
            'us-gaap:LongTermDebtCurrent', 
            'us-gaap:DebtCurrent',
            'us-gaap:LongTermDebt',
            'us-gaap:Liabilities',
            'us-gaap:LiabilitiesCurrent',
            'us-gaap:StockholdersEquity',
            'us-gaap:AssetsNet',
        ]

        for concept in common_bs_concepts:
            xpath = "//{concept}[@contextRef='{context}']".format(
                concept=concept,
                context=self.instant_context,
            )
            result_nodes = self.instance_root.xpath(
                xpath, 
                namespaces=self.ns
            )

            if len(result_nodes):
                unit_tag = result_nodes[0].attrib["unitRef"]
                currency = self.decode_units(unit_tag)
                break

        self.currency = currency

    def search(self, concept, context):
        """
        Searches a filing for a concept within a specific context

        Accounting concept values may have different formats and meanings: 
        
        A fact node's 'decimals' attribute is intended to provide the number
        of digits of precision for a concept value. If 'decimals' is positive,
        the number will always be a decimal. If 'decimals' is negative, it will
        always be an integer.

        **Note that the 'decimals' attribute is meant to show where rounding
        occurs in accounting concepts, so decimals='2' (e.g. 1.00) does not
        imply an exact monetary amount. In cases where EXACT values are 
        represented, decimals='INF' will be used.

        Python decimal.Decimal types are preferred here over other types to 
        maintain the precision in the concept value. Hence, even integers
        are returned as decimal.Decimal type.

        If the xsi:nil attribute is present and set to 'true', the value is nil, 
        which is interpreted here to mean 0.

        :param concept: a prefixed accounting concept (e.g. us-gaap:Cash)
        :type concept: str
        :param context_type: specify 'instant' or 'duration'
        :type context_type: str
        :rtype: decimal.Decimal or NoneType
        :return: the concept's value or None if concept is not found
        """
        node = None
        concept_value = None

        xpath_query = "//{concept}[@contextRef='{context}']".format(
            concept=concept,
            context=context,
        )
        results = self.instance_root.xpath(
            xpath_query, 
            namespaces=self.ns
        )

        if len(results):
            node = results[0]
            precision = node.attrib.get('decimals')
            nil_attribute = '{{{xsi}}}nil'.format(xsi=self.ns.get('xsi'))
            nil = node.attrib.get(nil_attribute)

            if nil and nil == 'true':
                concept_value = decimal.Decimal('0')
            else:
                concept_value = decimal.Decimal(node.text)

        return concept_value
            
    def check_end_date(end_date, fiscal_year_focus):
        """
        Checks validity of a filing end date and replaces it if necessary.

        For cases where no valid start date can be found, it is possible that an
        incorrect period end date was filed. This happened on NRG's 2015 annual
        filing, resulting in no matching start date or duration context. Try
        reconstructing the date with fiscal year focus in cases like this
        """
        year = int(fiscal_year_focus)
        dummy_start_date = end_date - timedelta(days=365)

        if dummy_start_date.year <= year <= end_date.year:
            # end_date seems reasonable
            return end_date_string
        else:
            # end_date appears to be wrong; make a guess using fiscal year focus
            month = end_date.month
            day = end_date.day
            best_guess_date = "{0}-{1}-{2}".format(year, month, day)
            return best_guess_date

    def monkey_patch(self, instance_file_path):
        """
        Attempts to find and fix problems with the filing's DEI stuff

        Incorrect or missing dei:DocumentPeriodEndDate and
        dei:DocumentFiscalYearFocus in particular can really cause a problem, 
        because they prevent the period's start date from being determined, 
        which prevents the duration context from loading correctly.
        """
        # Sometimes the fiscal year focus is just not there
        if not self.fiscal_year_focus:
            self.extract_year_from_period_end_date()

        # Sometimes the period end date has the wrong year
        if not self.period_start_date:

            # Use fiscal year focus to check and correct year
            self.period_end_date = check_end_date(
                self.period_end_date,
                self.fiscal_year_focus,
            )

            # Reload duration context
            self.get_current_duration_context()

        # Sometimes the period end date has the wrong day/month
        if not self.period_start_date:

            # Try using the date in the filename
            f = instance_file_path
            file_name = f.split('/')[-1]
            raw_date_string = file_name.split('-')[1].split('.')[0]
            date_string = raw_date_string[:4] + '-' \
                        + raw_date_string[4:6] + '-' \
                        + raw_date_string[6:]
            self.period_end_date = date_string

            # Reload duration context
            self.get_current_duration_context()

        # Wayne Savings Bancshares 2012 10-K dates are all fucked up
        if self.cik == '0001036030' and \
            self.fiscal_year_focus == '2012' and \
            self.document_type == '10-K':

                # Use wrong dates to load correct contexts
                self.period_start_date = '2011-04-01'
                self.period_end_date = '2011-12-31'

                # Reload contexts
                self.loadYear(0)

                # Now reset the dates correctly
                self.period_start_date = '2012-04-01'
                self.period_end_date = '2012-12-31'
                self.balance_sheet_date = '2012-12-31'

