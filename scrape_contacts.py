from itertools import islice
import json
import re

from bs4 import BeautifulSoup
import requests


SENATE_LIST_URL = 'http://senate.ca.gov/senators'
ASSEMBLY_LIST_URL = 'http://assembly.ca.gov/assemblymembers'

SENATE_NAME = 'views-field-field-senator-last-name'
SENATE_DISTRICT = 'views-field-field-senator-district'
SENATE_HOMEPAGE = 'views-field-field-senator-weburl'
SENATE_CAPITOL_OFFICE = 'views-field-field-senator-capitol-office'
SENATE_DISTRICT_OFFICE = 'views-field-field-senator-district-office'

ASSEMBLY_NAME_LINK = 'views-field-field-member-lname-sort'
ASSEMBLY_OFFICE = 'views-field-field-member-office-information'
ASSEMBLY_PARTY = 'views-field-field-member-party'
ASSEMBLY_DISTRICT = 'views-field-field-member-district'

SENATE_NAME_RE = re.compile(r'([^(]+) \((.+)\)')
ADDRESS_PHONE_RE = re.compile(r'([^(;]+)(;|<br />)?\s*(\(\d{3}\)\s*\d+-?\d+)')


def parse_address_phone(office):
    office = office.replace('\xa0', ' ').strip()
    try:
        match = ADDRESS_PHONE_RE.match(office)
        if match is not None:
            return match.group(1), match.group(3)
    except ValueError:
        pass

    raise ValueError("womp")
    print("Couldn't parse {} into an address and phone".format(office))
    return None, None


def build_district_offices(offices):
    update_dict = {}
    for idx, do in enumerate(offices):
        mail, phone = parse_address_phone(do)
        update_dict['district_office_{}_raw'.format(idx)] = do
        update_dict['district_mail_{}'.format(idx)] = mail
        update_dict['district_phone_{}'.format(idx)] = phone

    return update_dict


def get_senators():
    resp = requests.get(SENATE_LIST_URL)
    soup = BeautifulSoup(resp.content, 'html.parser', from_encoding='utf-8')

    roster = soup.find(class_='view-senator-roster')
    rows = roster.find_all(class_='views-row')

    senators = []
    for row in rows:
        name_party = row.find(class_=SENATE_NAME).find(class_='field-content').string
        name_match = SENATE_NAME_RE.match(name_party)

        capitol_office = row.find(class_=SENATE_CAPITOL_OFFICE).find('p').contents[0]
        district_office = row.find(class_=SENATE_DISTRICT_OFFICE).find('p')

        capitol_mail, capitol_phone = parse_address_phone(capitol_office)

        senator = {
            'name': name_match.group(1) if name_match is not None else name_party,
            'party': name_match.group(2) if name_match is not None else None,
            'district': list(row.find(class_=SENATE_DISTRICT).find(class_='field-content').stripped_strings)[1],
            'homepage': row.find(class_=SENATE_HOMEPAGE).find('a').attrs['href'],
            'capitol_office_raw': capitol_office,
            'capitol_mail': capitol_mail,
            'capitol_phone': capitol_phone,
        }

        senator.update(build_district_offices(district_office.stripped_strings))
        senators.append(senator)

    return senators


def get_assembly_reps():
    resp = requests.get(ASSEMBLY_LIST_URL)
    soup = BeautifulSoup(resp.content, 'html.parser', from_encoding='utf-8')

    roster = soup.find(class_='view-view-Members')
    rows = roster.table.tbody.find_all('tr')

    reps = []
    for row in rows:
        try:
            name_link = row.find(class_=ASSEMBLY_NAME_LINK).a
        except AttributeError:
            print(row)
        office = row.find(class_=ASSEMBLY_OFFICE)
        capitol_office = office.h3.next_sibling.strip()
        capitol_mail, capitol_phone = parse_address_phone(capitol_office)
        rep = {
            'name': name_link.string,
            'homepage': name_link.attrs['href'],
            'party': row.find(class_=ASSEMBLY_PARTY).string.strip(),
            'district': row.find(class_=ASSEMBLY_DISTRICT).string.strip(),
            'capitol_office_raw': capitol_office,
            'capitol_mail': capitol_mail,
            'capitol_phone': capitol_phone,
        }

        rep.update(build_district_offices(islice(office.p.strings, 0, None, 2)))
        reps.append(rep)

    return reps

if __name__ == '__main__':
    senators = get_senators()
    reps = get_assembly_reps()

    with open('senators.json', 'w') as senate_file:
        json.dump(senators, senate_file, indent=4)

    with open('assembly_representatives.json', 'w') as assembly_file:
        json.dump(reps, assembly_file, indent=4)
