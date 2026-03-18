import sys
from pprint import pprint
import pandas as pd
from tabulate import tabulate

import pathlib


class Sched:
    drop = []

    _raw = None

    @property
    def raw(self):
        if self._raw is not None:
            return self._raw
        # table = pd.read_html('sources/sources.html', flavor='html5lib', header=0)[0]

        tables = []

        for file in pathlib.Path('sources').iterdir():
            if not file.is_file():
                continue

            table = pd.read_html(file, flavor='html5lib', header=0)[0]

            tables.append(table)

        self._raw = pd.concat(tables)

        # normalize integer ids
        self._raw.reset_index(inplace=True, drop=True)

        if len(self._raw.columns) != len(self.headers):
            print(
                'Warning: table structure might have been changed!',
                file=sys.stderr
            )

        # set internal names instead of displayed ones
        self._raw.columns = schema

        return self._raw


class WeekSeparated:
    def get_upper():
        pass



class SchedByGroup(Sched, WeekSeparated):
    headers = [
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
    ],

    drop = [
        'lecturer',
        'department',
    ]


class SchedByLecturer(Sched, WeekSeparated):
    headers = [
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
    ],

    drop = [
        'lecturer',
        'department',
    ]


class SchedByClassroom(Sched):
    headers = [
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

    drop = [
        'classroom',
    ]


# TODO: CLI
# schema = classroom_table_schema
# schema = lecturer_table_schema
# drop = ['department']

wtletter = {
    "в": "upper",
    'н': "lower",
}

weeks = table.groupby('week', sort=False)
weeks = dict( iter(weeks) )
assert len(weeks) == 2, 'new week type?'

pd.set_option('display.max_rows', None)
print(repr(table))

serialized = {}

for wktp, w in weeks.items():
    # # remove column we're grouping by
    # w.drop(columns='week', inplace=True)

    # # strip trailing (not leading) nans in column 'discipline'
    # days = w.groupby('day')
    # # print(days.groups)
    # for _day, leclist in days.groups.items():
    #     for i in reversed(leclist):
    #         # print(w.loc[i].notna())
    #         if not w.loc[i].notna()['discipline']:
    #             break
    #         w.drop(index=i, inplace=True)

    # don't display some columns
    w.drop(columns=['lecturer', 'department'], inplace=True)

    # don't display NaNs
    w['subgroup'] = w['subgroup'].astype('Int8').astype('str').replace('<NA>', '')
    w.replace(pd.NA, '', inplace=True)

    # print(w)

    s_week = {}
    days = w.groupby('day', sort=False)
    for k, v in days:
    # remove column we're grouping by
        v.drop(columns='day', inplace=True)

        # s_week[k] = v.to_dict('index')
        s_week[k] = v.to_dict('records')

    wktp = wtletter[wktp]
    serialized[wktp] = s_week

# pprint(serialized)

headermap = dict(
    nlecture='№',
    group='группа',
    subgroup='п/гр',
    discipline='предмет',
    lecture_kind='тип занятия',
    lecturer='преподаватель',
    department='кафедра',
    classroom='аудитория',
)

wkdisplay = dict(
    upper='верхняя неделя',
    lower='нижняя неделя',
)

invert = dict(
    lower='upper',
    upper='lower',
)

for wktp, wk in serialized.items():
    with open(wktp + '.md', 'w', encoding='utf-8') as f:
        print(wkdisplay[wktp].capitalize(), file=f)
        print('===', file=f)
        print(file=f)

        inverted = invert[wktp] + '.md'

        print(
            f'[Другая неделя]({inverted})',
            file=f
        )

        print(file=f)
        for dayname, day in wk.items():
            print(dayname, file=f)
            print('---', file=f)
            print(file=f)

            day = day.copy()
            # del day['lecturer']
            # del day['department']

            t = tabulate(day, tablefmt='github', headers=headermap)

            print(t, file=f)
            print(file=f)
