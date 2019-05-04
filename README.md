# Deltafy XBRL

A Python library for working with 10-K/10-Q financial filings in XBRL format

## Usage

Use deltafy_xbrl's parser to easily access the document and entity information (DEI fields) in a financial filing or search for specific accounting concepts.

### Initialization

Load the instance document from an XBRL filing into an XBRLParser instance to examine its contents.

#### Example
```python
from deltafy_xbrl.parse import XBRLParser

example_filing = "xyz-20170101.xml"
xyz_corp_10k = XBRLParser(instance_file_path=example_filing)

print(xyz_corp_10k.registrant_name)
# 'XYZ Corp.'

print(xyz_corp_10k.document_type)
# '10-K'

print(xyz_corp_10k.fiscal_year_focus)
# 2016
```

#### XBRLParser Attributes

When a filing's instance document is loaded into an XBRLParser instance, the most common DEI fields and **current period** contexts will be loaded as attributes if they are present in the document:

Attribute Name | Type | Meaning
------------ | ------------- | -------------
amendment_flag | bool | Identifies whether the document is an amended filing
fiscal_year_end | str | The month and day upon which the fiscal year ends
fiscal_period_focus | str | The quarter represented by the filing or 'FY' for full-year
fisca_year_focus | int | The year in which the filing's accounting period occurred
period_end_date | datetime | The date upon which the filing's accounting period ended
document_type | str | '10-K' or '10-Q'
cik | str | The entity's central index key for SEC identification
current_reporting_status | bool | The entity's reporting status
filer_category | str | The entity's filer category
registrant_name | str | The name of the filing entity (a company, fund, etc.)
voluntary_filers | bool | The entity's voluntary filing status
well_known_issuer | bool | The entity's well-known issuer status
shell_company | bool | The entity's shell company status
small_business | bool | The entity's small business status
trading_symbols | list | A list of exchange trading symbols
currency | str | the **primary** currency used in the filing
instant_context | str | The context for instant concepts in the **current** period
duration_context | str | The context for duration concepts in the **current** period

### Search for Specific Financial Values

Once an instance document has been loaded, you can use the search method to find the value that was reported for specific accounting concepts. Use the prefixed accounting concept name and the desired context as parameters to the search function. The search method returned None in cases where no value is found.

#### Example
```python
current_instant = xbrl.instant_context
xbrl.search(concept="us-gaap:Cash", context=current_instant)
# Decimal('10000000')
```

Note that XBRLParser only loads the **current** instance and duration contexts for you, but there are potentially hundreds of contexts stored within a filing that may have associated values. These alternative contexts usually have no meaning in the current accounting period, but they are often included in XBRL instances so that tables can be constructed that show the values from multiple periods side by side.
