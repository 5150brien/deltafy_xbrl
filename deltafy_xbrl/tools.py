from datetime import datetime, timedelta

def delta_days(start_date_string, end_date_string):
    """ 
    Returns the number of days between two date strings (YYYY-MM-DD)
    """
    start_date = datetime.strptime(start_date_string, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d')
    return abs((end_date - start_date).days)

def full_year_period(start_date_string, end_date_string):
    """
    Returns True if year occurred between dates; otherwise returns False
    """
    full_year = False
    start_date = datetime.strptime(start_date_string, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d')

    if start_date.year == end_date.year:
        if abs(end_date.month - start_date.month) == 11:
            full_year = True
    else:   # Period spans two calendar years
        if end_date.month - start_date.month == 0 or \
            abs(end_date.month - start_date.month) == 1:
            # Cases like 02-01-2016 to 01-31-2017
            full_year = True
    return full_year

def count_months(start_date_string, end_date_string):
    """
    Returns the number of days between two date strings (YYYY-MM-DD)
    """
    start_date = datetime.strptime(start_date_string, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_string, '%Y-%m-%d')
    if start_date.year == end_date.year:
        total_months = end_date.month - start_date.month
    else:
        if (end_date.year - start_date.year) == 1:
            total_months = (12 - start_date.month) + end_date.month
        elif (end_date.year - start_date.year) > 1:
            year_adjustment = (end_date.year - start_date.year) * 12
            total_months = (12 - start_date.month) \
                            + end_date.month \
                            + year_adjustment
        else:
            # Negative years occurred (result of a filing error)
            total_months = 0
    return total_months

def strip_newlines(date_string):
    """
    Removes '\n' from dates in YYYY-MM-DD format
    """
    return date_string.replace('\n', '')

def check_fiscal_year_focus(fiscal_year_focus, start_date, end_date):
    """
    Checks validity of fiscal year focus and replaces it if necessary

    Some filers (Hibbett Sports, as an example) have submitted filings with
    an incorrect fiscal year focus. This can be checked by determining the
    year in which the largest portion of the accounting period occurred.
    """
    if start_date.year == end_date.year:
        if start_date.year != fiscal_year_focus:
            return start_date.year
    else:
        # The accounting period crosses calendar years
        start_year_end_date = datetime(start_date.year, 12, 31)
        end_year_start_date = datetime(end_date.year, 1, 1)
        start_year_days = (start_year_end_date - start_date).days
        end_year_days = (end_date - end_year_start_date).days

        if start_year_days > end_year_days:
            if start_date.year != fiscal_year_focus:
                return start_date.year
        elif start_year_days < end_year_days:
            if end_date.year != fiscal_year_focus:
                return end_date.year
        else:
            # Exactly the same days in both years
            if start_date.year != fiscal_year_focus and \
            end_date.year != fiscal_year_focus:
                return end_date.year

    return fiscal_year_focus

