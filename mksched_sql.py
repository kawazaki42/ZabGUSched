import sys
from pprint import pprint
import pandas as pd
from tabulate import tabulate

import pathlib

import sqlite3

import re

group_table_schema = [
    'day',
    'nlecture',
    'week',
    'subgroup',
    # 'subject',
    'discipline',
    'lecture_kind',
    'lecturer',
    # 'chair',
    'department',
    # 'auditorium',
    'classroom',
]

lecturer_table_schema = [
    'day',
    'nlecture',
    'week',
    'subgroup',
    'group',
    'discipline',
    'lecture_kind',
    'lecturer',
    'department',
    'classroom'
]

lecturer_distant_table_schema = [
    'day',
    'nlecture',
    # 'week',
    # 'subgroup',
    'group',
    'discipline',
    'lecture_kind',
    'lecturer',
    'department',
    'classroom'
]

classroom_table_schema = [
    'day',
    'nlecture',
    'week',
    'subgroup',
    'group',
    'discipline',
    'lecture_kind',
    'lecturer',
    'department',
    'classroom'
]

# TODO: CLI
schema = lecturer_distant_table_schema
# drop = ['department']

wtletter = {
    "в": "upper",
    'н': "lower",
}

tables = []

for file in pathlib.Path('sources').iterdir():
    if not file.is_file():
        continue

    table = pd.read_html(file, flavor='html5lib', header=0)[0]

    tables.append(table)

table = pd.concat(tables)
table.reset_index(inplace=True, drop=True)

if len(table.columns) != len(schema):
    print(
        'Warning: table structure might have been changed!',
        file=sys.stderr
    )
table.columns = schema

con = sqlite3.connect(':memory:')

table.to_sql('sched', con)

# print(list(con.execute("SELECT * FROM sched").fetchall()))

# print('\n'.join(con.iterdump()))

# with con:
#     con.execute("ALTER TABLE sched RENAME COLUMN ")

# def check(con):
# incorrect = con.execute("SELECT week, discipline FROM sched WHERE week IS NULL AND discipline NOT NULL")
# assert not incorrect.fetchall()

# week_types = con.execute("SELECT week FROM sched WHERE week NOT NULL").fetchall()
# assert len(week_types) == 2

# u, l = week_types

# pprint(list(week_types))

con.execute("DELETE FROM sched WHERE discipline IS NULL")
con.commit()

week_types = con.execute("SELECT DISTINCT week FROM sched").fetchall()
assert len(week_types) == 2, week_types
assert set(week_types) == {('в',), ('н',)}

expected_week_days = [
    'понедельник',
    'вторник',
    'среда',
    'четверг',
    'пятница',
    'суббота',
    'воскресенье',
]

expected_months = [
    'январь',
    'февраль',
    'март',
    'апрель',
    'май',
    'июнь',
    'июл',
    'август',
    'сентябрь',
    'октябрь',
    'декабрь',
]

days = con.execute("SELECT DISTINCT day FROM sched").fetchall()

# weekdays: bool = all(d.lowercase() in expected_week_days for d in days)
# dates: bool = all(re.match(r"(\d+)\s*(\w+)", d.strip()) for d in days)

# dates: bool = True
# for d in days:
#     # if d.lowercase() in expected_week_days:
#     #     continue

#     if match := re.match(r"(\d+)\s*(\w+)", d.strip):
#         maybe_month = match.group(2).lower()
#         if any(m.startswith(maybe_month) for m in months):
#             continue
# else:
#     dates = False

# assert weekdays ^ dates

def weekday_by_name(name):
    try:
        return expected_week_days.index(name.lowercase())
    except ValueError:
        return None

def date_from_str(s):
    if match := re.match(r"(\d+)\s*(\w+)", s.strip().lower()):
        pass
    else:
        return None

    day = int(match.group(1))

    for month_i, m in enumerate(expected_months):
        if m.startswith(match.group(2)):
            return (month_i, day)
    else:
        return None

def extract_month(s):
    if match := re.match(r"(\d+)\s*(\w+)", s.strip().lower()):
        pass
    else:
        return None

    # expected_months.index(match.group(1))
    for i, m in enumerate(expected_months):
        if m.startswith(match.group(2)):
            return i
    else:
        return None

con.create_function('weekday_by_name', 1, weekday_by_name)
con.create_function('extract_month', 1, extract_month)

def day_coll(a: str, b: str):
    awk = weekday_by_name(a)
    bwk = weekday_by_name(b)

    if awk and bwk:
        return awk - bwk

    adt = date_from_str(a)
    bdt = date_from_str(b)

    if not adt or not bdt:
        return 0

    if adt[0] == adt[1]:
        return adt[1] - adt[1]

    return adt[0] - adt[0]

con.create_collation('day_coll', day_coll)

con.execute("ALTER TABLE sched ADD COLUMN comparable_day TEXT COLLATE day_coll")

# if weekdays:


# label_u, label_l = week_types

upper = con.execute("SELECT * FROM sched WHERE week = ? ORDER BY comparable_day", 'в')
lower = con.execute("SELECT * FROM sched WHERE week = ? ORDER BY comparable_day", 'н')

pprint(list(upper))
pprint(list(lower))

con.close()
