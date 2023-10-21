import re
import pdfplumber

from pathlib import Path
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from parsers.model import Service

TARGET_PROVIDER = 'PROVIDENT'

overrideDuplicates = True # True = assume all 'duplicate' transactions are valid
debug = False # prints out one parsed PDF for you to manually test regex on

# ^(?P<service_type>Electric|Hot Water|Cold Water) (?P<reading_date>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]{0,6} ([0-9]{1,2}), ([0-9]{4}))  (?P<days>([0-9]{1,2}))  (?P<previous_reading>([0-9]{1,4}))  (?P<current_reading>([0-9]{1,4})) (?P<read_type>([a-zA-Z].*))  (?P<laf>([0-9]{1,3}.[0-9]{1,4}))  (?P<billed_consumption>([0-9]{0,4})) (?P<unit>(kWh|m³))

regexes = {
    'PROVIDENT': {
        'service': (r"^(?P<service_type>Electric|Hot Water|Cold Water) "
            r"(?P<reading_date>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]{0,6} ([0-9]{1,2}), ([0-9]{4}))  "
            r"(?P<days>([0-9]{1,2}))  "
            r"(?P<previous_reading>([0-9]{1,4}))  "
            r"(?P<current_reading>([0-9]{1,4})) "
            r"(?P<read_type>([a-zA-Z]{0,10}))  "
            r"(?P<laf>([0-9]{1,3}.[0-9]{1,4}))  "
            r"(?P<billed_consumption>([0-9]{0,4})) "
            r"(?P<unit>(kWh|m³))"),
        'electricity_rate': r'Electricity Charge.*@ (?P<electricity_rate>[0-9]{1,2}.[0-9]{1,4})',
        'hot_water_charge': r'Hot Water Charge  (?P<water_charge>[0-9]{0,1}.[0-9]{2})',
        'cold_water_charge': r'Cold Water Charge  (?P<water_charge>[0-9]{0,1}.[0-9]{2})',
        'total_amount': r'Total Amount.*(?P<total_amount>\$[0-9]{1,3}.[0-9]{2})'
    },
}

def get_services(data_directory):
    result = set()
    for pdf_path in Path(data_directory).rglob('*.pdf'):
        try: 
            result |= _parse_invoice(pdf_path)
        except Exception as e:
            print("Error for %s" % pdf_path)
            print(e)
    return result 

def _parse_invoice(pdf_path):
    result = set()
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        print("------------------------------------------")
        print(pdf_path)
        for page in pdf.pages:
            text += page.extract_text(x_tolerance=1)

        if (debug):
            print(text)
            exit()

        electricity_rate = _get_electricity_rate(text, TARGET_PROVIDER)
        hot_water_charge = _get_water_charge(text, TARGET_PROVIDER, True)
        cold_water_charge = _get_water_charge(text, TARGET_PROVIDER, False)
        total_amount = _get_total_amount(text, TARGET_PROVIDER)

        endOfYearWarning = False
        i = 0

        # debugging transaction mapping - all regexes in 'service' have to find a result in order for it to be considered a 'match'
        for match in re.finditer(regexes[TARGET_PROVIDER]['service'], text, re.MULTILINE | re.IGNORECASE | re.DOTALL):
            match_dict = match.groupdict()
            if (debug):
                print(match_dict)
            reading_date = match_dict['reading_date'].replace(',', '') # remove the comma: Oct 1, 2023 -> Oct 1 2023
            
            try:
                reading_date = datetime.strptime(reading_date, '%B %d %Y') # try October 1 first
            except: # yes I know this is horrible, but this script runs once if you download your .pdfs monthly, what do you want from me
                reading_date = datetime.strptime(reading_date, '%m %d %Y') # if it fails, 08 10 2021

            # need to account for current year (Jan) and previous year (Dec) in statements 
            endOfYearCheck = reading_date.strftime("%m")

            if (endOfYearCheck == '12' and endOfYearWarning == False):
                endOfYearWarning = True
            if (endOfYearCheck == '01' and endOfYearWarning):
                date = date + relativedelta(years = 1)

            # Get rate
            service_type = str(match_dict['service_type'])
            billed_consumption = int(match_dict['billed_consumption'])
            unit = str(match_dict['unit'])
            if (service_type == 'Electric'):
                rate = str(electricity_rate) + "/" + unit
            elif (service_type == 'Hot Water'):
                rate = str(hot_water_charge / billed_consumption) + "/" + unit
            elif (service_type == 'Cold Water'):
                rate = str(cold_water_charge / billed_consumption) + "/" + unit
            else:
                rate = '-1'
            
            service = Service(service_type,
                                str(reading_date.date().isoformat()),
                                str(match_dict['days']),
                                str(match_dict['previous_reading']),
                                str(match_dict['current_reading']),
                                str(match_dict['read_type']),
                                str(match_dict['laf']),
                                billed_consumption,
                                unit,
                                rate)
            
            if (service in result):
                if (overrideDuplicates):
                    service.service_type = service.service_type + " 2"    
                    result.add(service)
                else:
                    prompt = input("Duplicate service found for %s, on %s for %f. Do you want to add this again? " % (service.service_type, service.reading_date, service.billed_consumption + " " + service.unit)).lower()
                    if (prompt == 'y'):
                        service.service_type = service.service_type + " 2"    
                        result.add(service)
                    else:
                        print("Ignoring!")
            else:
                result.add(service)
    # _validate(closing_bal, opening_bal, result)
    return result

def _validate(closing_bal, opening_bal, transactions):
    # spend transactions are negative numbers.
    # net will most likely be a neg number unless your payments + cash back are bigger than spend
    # outflow is less than zero, so purchases
    # inflow is greater than zero, so payments/cashback

    # closing balance is a positive number
    # opening balance is only negative if you have a CR, otherwise also positive
    net = round(sum([r.amount for r in transactions]), 2)
    outflow = round(sum([r.amount for r in transactions if r.amount < 0]), 2)
    inflow = round(sum([r.amount for r in transactions if r.amount > 0]), 2)
    if round(opening_bal - closing_bal, 2) != net:
        print("* the diff is: %f vs. %f" % (opening_bal - closing_bal, net))
        print(f"* Opening reported at {opening_bal}")
        print(f"* Closing reported at {closing_bal}")
        print(f"* Transactions (net/inflow/outflow): {net} / {inflow} / {outflow}")
        print("* Parsed transactions:")
        for t in sorted(list(transactions), key=lambda t: t.date):
            print(t)
        raise AssertionError("Discrepancy found, bad parse :(. Not all transcations are accounted for, validate your transaction regex.")

def _get_electricity_rate(pdf_text, provider):
    print("Getting electricity rate...")
    match = re.search(regexes[provider]['electricity_rate'], pdf_text)
    rate = float(match.groupdict()['electricity_rate'])
    print("Electricity rate is: %f" % rate)
    return rate

def _get_water_charge(pdf_text, provider, hot=False):
    print("Getting water charge...")
    water_type = 'hot_water_charge' if hot else 'cold_water_charge'
    match = re.search(regexes[provider][water_type], pdf_text)
    charge = float(match.groupdict()['water_charge'])
    print(water_type + " is: %f" % charge)
    return charge

def _get_total_amount(pdf_text, provider):
    print("Getting total amount...")
    match = re.search(regexes[provider]['total_amount'], pdf_text)
    amount = float(match.groupdict()['total_amount'].replace(',', '').replace('$', ''))
    print("Total amount is: %f" % amount)
    return amount
