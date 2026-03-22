import contextlib
import io
import itertools
import pathlib
import re
import sqlite3
import sys
import textwrap
from pprint import pprint

import duckdb
import pandas as pd
from tabulate import tabulate


class Sched:
    drop = []

    # _db = None

    # @property
    # def db(self):
    # if self._db is None:
    #     self._db = sqlite3.connect(":memory:")

    #     # self._db.set_trace_callback(print)
    #     self.raw.to_sql("sched", self._db)
    #     # self._db.set_trace_callback(None)

    #     self._db.execute("DELETE FROM sched WHERE discipline IS NULL")
    #     self._db.commit()

    #     self._db.row_factory = sqlite3.Row

    #     # for line in self._db.iterdump():
    #     #     print(line)

    # return self._db

    # return duckdb.sql("SELECT * FROM sched WHERE discipline NOT NULL").df()

    input_path = "sources"

    _raw = None

    @property
    def raw(self):
        if self._raw is not None:
            return self._raw
        # table = pd.read_html('sources/sources.html', flavor='html5lib', header=0)[0]

        tables = []

        for file in pathlib.Path(self.input_path).iterdir():
            if not file.is_file():
                continue

            table = pd.read_html(file, flavor="html5lib", header=0)[0]

            tables.append(table)

        self._raw = pd.concat(tables)

        # normalize integer ids
        self._raw.reset_index(inplace=True, drop=True)

        if len(self._raw.columns) != len(self.headers):
            print("Warning: table structure might have been changed!", file=sys.stderr)

        # set internal names instead of displayed ones
        self._raw.columns = self.headers

        # duckdb.register("raw", self._raw)

        # print(self._raw, file=sys.stderr)

        return self._raw

    wkday_names = [
        "понедельник",
        "вторник",
        "среда",
        "четверг",
        "пятница",
        "суббота",
        "воскресенье",
    ]

    # wkday_idx_by_name = {name: idx for (idx, name) in enumerate(wkday_names)}

    month_names = [
        "январь",
        "февраль",
        "март",
        "апрель",
        "май",
        "июнь",
        "июль",
        "август",
        "сентябрь",
        "октябрь",
        "декабрь",
    ]

    date_regex = re.compile(r"\s*(\d+)\s*(\w+)\s*")

    @classmethod
    def day_cmp_key(cls, day: str):
        try:
            return cls.wkday_names.index(day.strip())
        except ValueError:
            pass

        if match := cls.date_regex.fullmatch(day):
            n, maybe_month = match.groups()

            n = int(n)

            for i, name in cls.month_names:
                if name.startswith(maybe_month.lower()):
                    return (maybe_month, n)

        # shouldn't happen
        return day

    def by_day(self):
        return sorted(
            self.raw.groupby("day", sort=False), key=lambda kv: self.day_cmp_key(kv[0])
        )

    def _format_day(self, dname, leclist: pd.DataFrame):
        reclist = (
            leclist.drop(columns=self.drop + ["day", "week"])
            .dropna(subset="discipline")
            .to_dict("records")
        )

        # new_reclist = [dict(nlecture=i + 1) for i in range(6)]
        new_reclist = {}
        for rec in reclist:
            n = rec["nlecture"]
            new_rec = {}
            new_reclist[n] = new_rec
            # new_reclist.append(new_rec)
            # itertools.dropwhile()
            for k, v in rec.items():
                new_rec[k] = v

        for i in range(6):
            new_reclist.setdefault(i + 1, dict(nlecture=i + 1, discipline="пусто"))

        new_reclist = [new_reclist[i + 1] for i in range(6)]

        pprint(new_reclist, stream=sys.stderr)
        # leclist['discipline'].isna
        table = tabulate(
            # leclist,
            new_reclist,
            tablefmt="github",
            # headers=[headermap[k] for k in leclist.columns],
            headers="keys",
            showindex=False,
        )
        return textwrap.dedent(
            """
            {dname}
            ---

            {table}

            """[1:]
        ).format(
            dname=dname,
            table=table,
        )

    # def _by_day(self):
    #     # days = (w. for w in self.by_week())
    #     cols = self.headers
    #     cols = (s for s in cols if s not in self.drop and s != "day")
    #     cols = (f'"{s}"' for s in cols)
    #     cols = ", ".join(cols)
    #     days = self.db.execute("SELECT DISTINCT day FROM sched").fetchall()

    #     days.sort(key=self.day_cmp_key)

    #     self._days = days

    #     for d in days:
    #         # yield d, self.db.execute(f"SELECT {cols} FROM sched WHERE day = ?", (d,))
    #         self.db.execute(
    #             f"CREATE VIEW sched_day_{d} AS SELECT {cols} FROM sched WHERE day = ?",
    #             (d,),
    #         )


class WeekSeparated(Sched):
    week_labels = {
        "в": "upper",
        "н": "lower",
    }
    # db: sqlite3.Connection
    # _weeks = None
    # raw: pd.DataFrame

    # def _split(self):
    #     if self._weeks is not None:
    #         return

    #     weeks = self._raw.groupby('week', sort=False)
    #     self._weeks = dict( iter(weeks) )
    #     assert len(self._weeks) == 2, 'new week type?'

    # def get_upper(self):
    #     self._split()
    #     return self._weeks['в']

    # def get_lower(self):
    #     self._split()
    #     return self._weeks['н']

    # def _by_day_and_week(self):
    #     self._by_day()
    #     # u = (row for row in self.by_day() if row['week'] == 'в')
    #     # l = (row for row in self.by_day() if)
    #     cols = self.headers
    #     cols = (s for s in cols if s not in self.drop + ["day", "week"])
    #     cols = (f'"{s}"' for s in cols)
    #     cols = ", ".join(cols)
    #     # # print(list(cols))
    #     # # return self.db.executemany('SELECT ? FROM sched WHERE week = ?', [(cols, 'в'), (cols, 'н')])
    #     # # self.db.set_trace_callback(print)
    #     # # return self.db.executemany(f'SELECT {cols} FROM sched WHERE week = ?', [('в',), ('н',)])
    #     for d in self._days:
    #         u = self.db.execute(
    #             f"SELECT {cols} FROM sched_day_{d} WHERE week = ?", ("в",)
    #         )
    #         l = self.db.execute(
    #             f"SELECT {cols} FROM sched_day_{d} WHERE week = ?", ("н",)
    #         )
    #         yield u, l

    #     # return u, l

    # def by_week(self):
    #     return zip(*self._by_day_and_week())

    # def by_week(self):
    #     groups = self.raw.groupby('week', sort=False)
    #     return groups.loc['в'], groups['н']

    # def transform(self):
    #     weeks = tuple(self.by_week())
    #     assert len(weeks) == 2, 'new week type?'

    def by_week(self):
        # duckdb.register("by_day", self.by_day())
        for dname, day in self.by_day():
            # yield duckdb.executemany(
            #     "SELECT * EXCLUDING (week) FROM day WHERE week = ?", ["в", "н"]
            # ).df()
            yield dname, dict(list(day.groupby("week", sort=False)))

    # def _print_day(self, dname, leclist):
    #     print(dname)
    #     print("---")
    #     print()

    #     t = tabulate(leclist, tablefmt="github", headers=headermap)
    #     print(t)
    #     print()

    # def _print_one_week(self, week_code, prefix=""):
    def _print_one_week(self, week_code, prefix=""):
        # file = file or io.StringIO()
        # with contextlib.redirect_stdout(file):

        # header = wkdisplay[week_code].capitalize()
        # print(header)
        # print("===")
        # print()

        # other = invert[week_code] + ".md"
        # print(f"[Другая неделя]({other})")
        # print()

        print(prefix)

        # result = prefix

        for dname, day in self.by_week():
            leclist = day[week_code]
            # result += self._format_day(dname, leclist)
            # self._print_day(dname, leclist)
            print(self._format_day(dname, leclist))

        # return result

    def dump(self):
        prefix = textwrap.dedent(
            """
            {header}
            ===

            [Другая неделя]({invert_link})

            """[1:]
        )

        with (
            open("upper.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "в",
                prefix.format(
                    header=wkdisplay["в"].capitalize(),
                    invert_link=invert["в"] + ".md",
                ),
            )

        with (
            open("lower.md", "w", encoding="utf8") as f,
            contextlib.redirect_stdout(f),
        ):
            self._print_one_week(
                "н",
                prefix.format(
                    header=wkdisplay["н"].capitalize(),
                    invert_link=invert["н"] + ".md",
                ),
            )


class SchedByGroup(WeekSeparated):
    input_path = "sources/by_group"

    headers = [
        "day",
        "nlecture",
        "week",
        "subgroup",
        # 'subject',
        "discipline",
        "lecture_kind",
        "lecturer",
        # 'chair',
        "department",
        # 'auditorium',
        "classroom",
    ]

    drop = [
        "lecturer",
        "department",
    ]


class SchedByLecturer(WeekSeparated):
    input_path = "sources/by_lecturer"

    headers = [
        "day",
        "nlecture",
        "week",
        "subgroup",
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]

    drop = [
        "lecturer",
        "department",
    ]


class SchedByClassroom(Sched):
    input_path = "sources/by_classroom"

    headers = [
        "day",
        "nlecture",
        "week",
        "subgroup",
        "group",
        "discipline",
        "lecture_kind",
        "lecturer",
        "department",
        "classroom",
    ]

    drop = [
        "classroom",
    ]


# TODO: CLI
# schema = classroom_table_schema
# schema = lecturer_table_schema
# drop = ['department']

# # pd.set_option('display.max_rows', None)
# # print(repr(table))

# serialized = {}

"""
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
"""

headermap = dict(
    nlecture="№",
    group="группа",
    subgroup="п/гр",
    discipline="предмет",
    lecture_kind="тип занятия",
    lecturer="преподаватель",
    department="кафедра",
    classroom="аудитория",
)

# wkdisplay = dict(
#     upper="верхняя неделя",
#     lower="нижняя неделя",
# )

wkdisplay = dict(
    в="верхняя неделя",
    н="нижняя неделя",
)

# invert = dict(
#     lower="upper",
#     upper="lower",
# )

invert = dict(
    в="lower",
    н="upper",
)

SchedByLecturer().dump()

# u, l = SchedByLecturer().by_week()

# m = dict(upper=u, lower=l)

# for wktp, wk in m.items():
#     with open(wktp + ".md", "w", encoding="utf-8") as f:
#         print(wkdisplay[wktp].capitalize(), file=f)
#         print("===", file=f)
#         print(file=f)

#         inverted = invert[wktp] + ".md"

#         print(f"[Другая неделя]({inverted})", file=f)

#         print(file=f)
#         for dayname, day in wk.items():
#             print(dayname, file=f)
#             print("---", file=f)
#             print(file=f)

#             day = day.copy()
#             # del day['lecturer']
#             # del day['department']

#             t = tabulate(day, tablefmt="github", headers=headermap)

#             print(t, file=f)
#             print(file=f)

# print(*SchedByLecturer().db.iterdump(), sep='\n')


# with open('upper.md', 'w', encoding='utf8') as f:


# pprint(l.fetchall())

# print(l)
